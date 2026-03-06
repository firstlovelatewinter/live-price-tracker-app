#!/usr/bin/env python3
"""
Background price monitor for Uniqlo products.
Runs scheduled price checks and can send notifications.
"""

import schedule
import time
import sys
import os
import asyncio
import random
import discord
from datetime import datetime
from database import get_all_products, record_price, update_product_info, init_db
from scraper import check_price
from notifications import notify_price_drop
import pytz


def check_all_products():
    """Check prices for all tracked products."""
    print(f"\n{'='*60}")
    print(f"Running scheduled price check at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    products = get_all_products()

    if not products:
        print("No products to check. Add some products first!")
        return

    checked = 0
    updated = 0
    errors = 0

    for product in products:
        result = check_price(product['url'])

        if result.get('error'):
            print(f"  ✗ Error checking product {product['id']}: {result['error']}")
            errors += 1
            continue

        # Record the price
        record_price(
            product_id=product['id'],
            price=result['current_price'],
            original_price=result['original_price'],
            is_on_sale=result['is_on_sale'],
            sizes_available=result.get('sizes_available', [])
        )

        # Update product info if needed
        update_info = {}
        if result['name'] and not product.get('name'):
            update_info['name'] = result['name']
        if result.get('image_url') and not product.get('image_url'):
            update_info['image_url'] = result['image_url']
        if update_info:
            update_product_info(product['id'], **update_info)

        checked += 1

        # Check for price changes
        from database import get_price_history
        history = get_price_history(product['id'], limit=2)

        if len(history) >= 2:
            old_price = history[1]['price']
            new_price = history[0]['price']

            if new_price < old_price:
                print(f"  ✓ {result['name']}: PRICE DROPPED ${old_price:.2f} → ${new_price:.2f}")
                updated += 1
                # The product dict needs the URL to be included in the notification
                product_with_url = {**result, 'url': product['url']}
                notify_price_drop(product_with_url)

            elif new_price > old_price:
                print(f"  ✓ {result['name']}: Price increased ${old_price:.2f} → ${new_price:.2f}")
            else:
                print(f"  ✓ {result['name']}: ${new_price:.2f} (no change)")
        else:
            print(f"  ✓ {result['name']}: ${result['current_price']:.2f} (first check)")

    print(f"\nSummary: {checked} checked, {updated} price drops found, {errors} errors")
    print(f"{'='*60}\n")




def run_scheduler(interval_hours=6):
    """Run the price checker on a schedule."""
    print(f"Starting price monitor (checking every {interval_hours} hours)...")
    print("Press Ctrl+C to stop\n")

    # Schedule the job
    schedule.every(interval_hours).hours.do(check_all_products)

    # Run once immediately
    check_all_products()

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
        sys.exit(0)


def run_daily_at_6am_est():
    """Run the price checker daily at 6:00 AM EST."""
    eastern = pytz.timezone('US/Eastern')
    print("Starting price monitor (checking daily at 6:00 AM EST)...")
    print("Press Ctrl+C to stop\n")

    # Schedule for 6am EST
    schedule.every().day.at("06:00").do(check_all_products)

    # Show next run time
    now = datetime.now(eastern)
    next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now.hour >= 6:
        next_run = next_run.replace(day=now.day + 1)
    print(f"Next scheduled check: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Run once immediately on startup
    check_all_products()

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
        sys.exit(0)


def run_twice_daily_est():
    """Run the price checker daily at 6:00 AM and 6:00 PM EST."""
    eastern = pytz.timezone('US/Eastern')
    print("Starting price monitor (checking daily at 6:00 AM and 6:00 PM EST)...")
    print("Press Ctrl+C to stop\n")

    # Schedule for 6am and 6pm EST
    schedule.every().day.at("06:00").do(check_all_products)
    schedule.every().day.at("18:00").do(check_all_products)

    # Run once immediately on startup
    check_all_products()

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
        sys.exit(0)

def run_once():
    """Run a single price check."""
    check_all_products()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Uniqlo Price Monitor')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=6, help='Check interval in hours (default: 6)')
    parser.add_argument('--daily-6am-est', action='store_true', help='Check daily at 6:00 AM EST')
    parser.add_argument('--twice-daily-est', action='store_true', help='Check daily at 6:00 AM and 6:00 PM EST')
    parser.add_argument('--init', action='store_true', help='Initialize database and exit')

    args = parser.parse_args()


    # Initialize database
    init_db()

    if args.init:
        print("Database initialized.")
        sys.exit(0)

    if args.once:
        run_once()
    elif args.daily_6am_est:
        run_daily_at_6am_est()
    elif args.twice_daily_est:
        run_twice_daily_est()
    else:
        run_scheduler(args.interval)
