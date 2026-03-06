
import asyncio
from playwright.async_api import async_playwright
import re
import json
from urllib.parse import urlparse
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

STORES = {
    'uniqlo.com': 'Uniqlo',
    'ae.com': 'Aerie',
}

def get_store_from_url(url: str) -> str:
    """Identify the store from the product URL."""
    domain = urlparse(url).netloc.replace('www.', '')
    return STORES.get(domain)

# --- Store-Specific Scraping Logic ---
STORE_SELECTORS = {
    'Uniqlo': {
        'price': '.fr-ec-price-text',
        'original_price': '.fr-ec-price-was',
    },
    'Aerie': {
        # Look for a sale price first, fall back to the list price you provided.
        'price': '[data-testid="sale-price"], [data-testid="list-price"]',
        'original_price': '[data-testid="list-price"]',
    }
}


async def _scrape_single_page(page, url: str) -> Dict[str, Any]:
    """Helper to scrape data from a single Playwright page using store-specific selectors."""
    store_name = get_store_from_url(url)
    selectors = STORE_SELECTORS.get(store_name)

    result = { 'current_price': None, 'original_price': None, 'is_on_sale': False, 'name': None, 'image_url': None, 'error': None }

    if not selectors:
        result['error'] = f"No selectors defined for store: {store_name}"
        logging.warning(result['error'])
        await page.close()
        return result

    try:
        await page.goto(url, wait_until='load', timeout=60000)

        # --- Price (Primary) ---
        price_locator = page.locator(selectors['price']).first
        await price_locator.wait_for(timeout=20000)
        price_text = await price_locator.inner_text()
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            result['current_price'] = float(price_match.group())

        # --- Name, Original Price, Image (Best Effort) ---
        try: result['name'] = await page.title()
        except: pass
        try:
            original_price_locator = page.locator(selectors['original_price']).first
            original_price_text = await original_price_locator.inner_text(timeout=5000)
            op_match = re.search(r'[\d,]+\.?\d*', original_price_text.replace(',', ''))
            if op_match:
                original_price = float(op_match.group())
                if result['current_price'] and original_price > result['current_price']:
                    result['original_price'] = original_price
                    result['is_on_sale'] = True
        except: pass
        try:
            og_image = await page.locator('meta[property="og:image"]').get_attribute('content')
            if og_image: result['image_url'] = og_image
        except: pass

    except Exception as e:
        result['error'] = f"Failed to scrape {url} for {store_name}: {str(e)}"
        logging.warning(result['error'])
    finally:
        await page.close()
    return result

async def async_check_prices_in_batch(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Highly efficient batch scraper using one browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        async def scrape_task(product):
            page = await context.new_page()
            scraped_data = await _scrape_single_page(page, product['url'])
            return {**product, **scraped_data}
        tasks = [scrape_task(p) for p in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()
    return results

def check_price(url: str) -> dict:
    """Synchronous wrapper for a single URL check."""
    store = get_store_from_url(url)
    if not store: return {'error': f"Unsupported store domain for URL: {url}"}
    product_stub = {'url': url, 'id': 0, 'store': store}
    return asyncio.run(async_check_prices_in_batch([product_stub]))[0]

if __name__ == "__main__":
    # You can add test URLs here for quick testing
    test_url = input("Enter a product URL to test: ").strip()
    if test_url:
        result = check_price(test_url)
        print(json.dumps(result, indent=2))
