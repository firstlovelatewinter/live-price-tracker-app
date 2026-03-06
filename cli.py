#!/usr/bin/env python3
"""
Command-line interface for managing the Uniqlo price monitor.
"""

import argparse
import sys
from database import (
    init_db, get_all_products, add_product, delete_product,
    get_price_history, update_product_info, record_price
)
from scraper import check_price


def cmd_list(args):
    """List all tracked products."""
    products = get_all_products()

    if not products:
        print("No products tracked yet.")
        return

    print(f"\n{'ID':<5} {'Name':<40} {'Price':<12} {'Last Checked':<20}")
    print("-" * 80)

    for p in products:
        name = (p['name'] or 'Unknown')[:38]
        price = f"${p['current_price']:.2f}" if p['current_price'] else "Not checked"
        last = p['last_checked'] or "Never"
        print(f"{p['id']:<5} {name:<40} {price:<12} {last:<20}")

    print(f"\nTotal: {len(products)} products")


def cmd_add(args):
    """Add a new product to track."""
    url = args.url
    name = args.name

    if not url.startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)

    print(f"Adding product...")
    product_id, created = add_product(url, name)

    if not created:
        print("This is already tracked!")
        sys.exit(0)

    # Immediately check the price
    print("Checking initial price...")
    result = check_price(url)

    if result.get('error'):
        print(f"Warning: Could not fetch price - {result['error']}")
        print(f"Product added (ID: {product_id}) but price not recorded.")
    else:
        record_price(
            product_id=product_id,
            price=result['current_price'],
            original_price=result['original_price'],
            is_on_sale=result['is_on_sale'],
            sizes_available=result['sizes_available']
        )

        # Update name if we got one
        if result['name'] and not name:
            update_product_info(product_id, name=result['name'])

        print(f"✓ Product added (ID: {product_id})")
        print(f"  Name: {result['name']}")
        print(f"  Price: ${result['current_price']:.2f}")
        if result['original_price']:
            print(f"  Original: ${result['original_price']:.2f} (SALE!)")


def cmd_remove(args):
    """Remove a product from tracking."""
    delete_product(args.id)
    print(f"✓ Removed product {args.id}")


def cmd_check(args):
    """Check all product prices now."""
    from monitor import check_all_products
    check_all_products()


def cmd_history(args):
    """Show price history for a product."""
    history = get_price_history(args.id, limit=args.limit)

    if not history:
        print(f"No price history found for product {args.id}")
        return

    # Get product info
    products = get_all_products()
    product = next((p for p in products if p['id'] == args.id), None)

    if product:
        print(f"\nPrice history for: {product['name'] or 'Unknown Product'}")
        print(f"URL: {product['url']}")
    else:
        print(f"\nPrice history for product ID: {args.id}")

    print(f"\n{'Date':<20} {'Price':<12} {'Status':<15}")
    print("-" * 50)

    prev_price = None
    for h in history:
        date = h['checked_at']
        price = f"${h['price']:.2f}"

        if prev_price is None:
            status = "First check"
        elif h['price'] < prev_price:
            status = "↓ Price drop"
        elif h['price'] > prev_price:
            status = "↑ Price up"
        else:
            status = "→ No change"

        if h['is_on_sale']:
            status += " (SALE)"

        print(f"{date:<20} {price:<12} {status:<15}")
        prev_price = h['price']


def main():
    parser = argparse.ArgumentParser(
        description='Uniqlo Price Monitor CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                          # Show all tracked products
  %(prog)s add <url>                     # Add a product
  %(prog)s add <url> -n "My Product"     # Add with custom name
  %(prog)s check                         # Check all prices now
  %(prog)s history 1                     # Show history for product 1
  %(prog)s remove 1                      # Remove product 1
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List all tracked products')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a product to track')
    add_parser.add_argument('url', help='Uniqlo product URL')
    add_parser.add_argument('-n', '--name', help='Optional product name')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a product')
    remove_parser.add_argument('id', type=int, help='Product ID')

    # Check command
    subparsers.add_parser('check', help='Check all prices now')

    # History command
    history_parser = subparsers.add_parser('history', help='Show price history')
    history_parser.add_argument('id', type=int, help='Product ID')
    history_parser.add_argument('-l', '--limit', type=int, default=20,
                               help='Number of entries to show (default: 20)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize database
    init_db()

    # Dispatch to command handler
    commands = {
        'list': cmd_list,
        'add': cmd_add,
        'remove': cmd_remove,
        'check': cmd_check,
        'history': cmd_history,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
