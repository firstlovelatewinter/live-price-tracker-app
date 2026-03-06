
import os
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, flash, jsonify
from database import get_all_products, get_price_history, add_product, delete_product, init_db, record_price
from scraper import check_price, async_check_prices_in_batch

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Thread-safe, robust background task management ---
class PriceChecker:
    def __init__(self, check_interval_minutes=5):
        self._lock = threading.Lock()
        self._thread = None
        self.status = "idle"  # idle, running
        self.last_run_completion = None
        self.check_interval = timedelta(minutes=check_interval_minutes)

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def needs_check(self):
        if self.last_run_completion is None:
            return True
        return datetime.now() - self.last_run_completion > self.check_interval

    def start(self):
        with self._lock:
            if self.is_running():
                logging.info("Skipping price check start; one is already running.")
                return False
            if not self.needs_check():
                logging.info(f"Skipping price check; last run was less than {self.check_interval} ago.")
                return False

            self.status = "running"
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logging.info("Started background price check thread.")
            return True

    def _run(self):
        logging.info("Background thread: Starting price check for all products...")
        all_prods_from_db = get_all_products()

        try:
            scraped_results = asyncio.run(async_check_prices_in_batch(all_prods_from_db))
            for result in scraped_results:
                if isinstance(result, dict) and not result.get('error') and result.get('current_price') is not None:
                    record_price(
                        product_id=result['id'],
                        price=result['current_price'],
                        original_price=result.get('original_price'),
                        is_on_sale=result.get('is_on_sale', False),
                        sizes_available=result.get('sizes_available', [])
                    )
                else:
                    logging.warning(f"Skipping DB update for failed scrape: {result}")
        except Exception as e:
            logging.error(f"Exception in background price check: {e}", exc_info=True)
        finally:
            self.last_run_completion = datetime.now()
            self.status = "idle"
            logging.info("Background thread: Price check completed.")

price_checker = PriceChecker()

def process_product_changes(products):
    """Calculate price changes for a list of products."""
    for p in products:
        if p.get('current_price') is not None:
            history = get_price_history(p['id'], limit=2)
            if len(history) >= 2:
                prev, curr = history[1]['price'], history[0]['price']
                if curr < prev: p['price_change'] = 'down'; p['price_diff'] = round(prev - curr, 2)
                elif curr > prev: p['price_change'] = 'up'; p['price_diff'] = round(curr - prev, 2)
                else: p['price_change'] = 'same'
            else: p['price_change'] = 'new'
    return products

from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
auth = HTTPBasicAuth()

# --- User credentials, loaded from environment variables ---
users = {
    os.environ.get("HTTP_USERNAME"): generate_password_hash(os.environ.get("HTTP_PASSWORD"))
}

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

@app.route('/')
@auth.login_required
def index():
    # Attempt to start a background check if needed and not already running
    price_checker.start()

    # Always render immediately with data from the database
    products = get_all_products()
    products = process_product_changes(products)

    stores = sorted(list(set(p['store'] for p in products if p['store'])))
    selected_store = request.args.get('store')

    display_products = products
    if selected_store:
        display_products = [p for p in products if p['store'] == selected_store]
    else:
        display_products.sort(key=lambda p: (
            0 if p.get('price_change') in ['up', 'down'] else 1,
            p.get('last_checked', '') or 'a'
        ), reverse=False)

    return render_template('index.html',
                           products=display_products,
                           stores=stores,
                           selected_store=selected_store,
                           now=datetime.now())

@app.route('/status')
@auth.login_required
def get_status():
    """Endpoint for the frontend to poll for status updates."""
    return jsonify({"status": price_checker.status})

@app.route('/add', methods=['POST'])
@auth.login_required
def add_product_route():
    url = request.form.get('url', '').strip()
    if not url: return "URL is required", 400
    result = check_price(url)
    if result.get('error'):
        flash(f"Error checking URL: {result['error']}", "error")
        return redirect('/')
    store = result.get('store')
    product_id, created = add_product(url, store=store, name=result.get('name'), image_url=result.get('image_url'))
    if not created:
        flash(f"This product is already tracked (ID: {product_id}).", "info")
    elif result and not result.get('error'):
        record_price(product_id=product_id, price=result['current_price'], original_price=result.get('original_price'), is_on_sale=result.get('is_on_sale', False), sizes_available=result.get('sizes_available', []))
    price_checker.last_run_completion = None # Invalidate to trigger a new check on next load
    return redirect('/?refresh=true')

@app.route('/delete/<int:product_id>', methods=['POST'])
@auth.login_required
def delete_product_route(product_id):
    delete_product(product_id)
    return redirect('/')

if __name__ == '__main__':
    init_db()
    price_checker.start() # Start a check on application startup
    app.run(debug=True, host='0.0.0.0', port=5002)
