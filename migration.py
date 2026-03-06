import sqlite3
from pathlib import Path

def migrate_data():
    source_db_path = Path("/Users/LeAnnLo/uniqlo-price-monitor/prices.db")
    dest_db_path = Path(__file__).parent / "prices.db"

    if not source_db_path.exists():
        print(f"Source database not found at {source_db_path}")
        return

    print(f"Source: {source_db_path}")
    print(f"Destination: {dest_db_path}")

    source_conn = sqlite3.connect(source_db_path)
    source_conn.row_factory = sqlite3.Row
    source_cursor = source_conn.cursor()

    dest_conn = sqlite3.connect(dest_db_path)
    dest_cursor = dest_conn.cursor()

    # Initialize the destination database just in case it's empty
    from database import init_db
    init_db()

    # Get all products from the source
    source_cursor.execute("SELECT * FROM products")
    products = source_cursor.fetchall()

    migrated_count = 0
    skipped_count = 0

    for product in products:
        product_dict = dict(product)

        # Check if product URL already exists in destination
        dest_cursor.execute("SELECT id FROM products WHERE url = ?", (product_dict['url'],))
        existing_product = dest_cursor.fetchone()

        if existing_product:
            print(f"Skipping product (already exists): {product_dict['url']}")
            skipped_count += 1
            continue

        # Insert the new product
        dest_cursor.execute(
            """
            INSERT INTO products (url, store, name, product_code, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                product_dict['url'],
                product_dict.get('store', 'Uniqlo'), # Set default store
                product_dict['name'],
                product_dict['product_code'],
                product_dict['image_url'],
                product_dict['created_at'],
            )
        )
        new_product_id = dest_cursor.lastrowid

        # Get all price history for this product from the source
        source_cursor.execute("SELECT * FROM price_history WHERE product_id = ?", (product_dict['id'],))
        price_history = source_cursor.fetchall()

        for history_entry in price_history:
            history_dict = dict(history_entry)
            dest_cursor.execute(
                """
                INSERT INTO price_history (product_id, price, original_price, is_on_sale, sizes_available, checked_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_product_id,
                    history_dict['price'],
                    history_dict['original_price'],
                    history_dict['is_on_sale'],
                    history_dict['sizes_available'],
                    history_dict['checked_at'],
                )
            )

        migrated_count += 1
        print(f"Migrated product: {product_dict['url']} (New ID: {new_product_id})")

    dest_conn.commit()

    source_conn.close()
    dest_conn.close()

    print(f"\nMigration complete!")
    print(f"Migrated {migrated_count} new products.")
    print(f"Skipped {skipped_count} existing products.")

if __name__ == "__main__":
    migrate_data()
