import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "prices.db"


def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table for products being tracked
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            store TEXT,
            name TEXT,
            product_code TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for price history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            original_price DECIMAL(10,2),
            is_on_sale BOOLEAN DEFAULT 0,
            sizes_available TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized.")


def add_product(url: str, store: str = None, name: str = None, product_code: str = None, image_url: str = None) -> tuple[int, bool]:
    """Add a new product to track. Returns (product_id, created)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO products (url, store, name, product_code, image_url) VALUES (?, ?, ?, ?, ?)",
            (url, store, name, product_code, image_url)
        )
        conn.commit()
        product_id = cursor.lastrowid
        print(f"Added product: {name or url} (ID: {product_id})")
        return product_id, True
    except sqlite3.IntegrityError:
        # Product already exists, get its ID
        cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
        product_id = cursor.fetchone()[0]
        return product_id, False
    finally:
        conn.close()


def record_price(product_id: int, price: float, original_price: float = None,
                 is_on_sale: bool = False, sizes_available: list = None):
    """Record a new price entry for a product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sizes_json = json.dumps(sizes_available) if sizes_available else None

    cursor.execute("""
        INSERT INTO price_history (product_id, price, original_price, is_on_sale, sizes_available)
        VALUES (?, ?, ?, ?, ?)
    """, (product_id, price, original_price, is_on_sale, sizes_json))

    conn.commit()
    conn.close()


def get_all_products():
    """Get all tracked products with their latest price info."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        WITH latest_prices AS (
            SELECT
                product_id,
                price,
                original_price,
                is_on_sale,
                checked_at,
                ROW_NUMBER() OVER(PARTITION BY product_id ORDER BY checked_at DESC) as rn
            FROM price_history
        )
        SELECT
            p.id, p.url, p.store, p.name, p.product_code, p.image_url, p.created_at,
            lp.price as current_price,
            lp.original_price as original_price,
            lp.is_on_sale as is_on_sale,
            lp.checked_at as last_checked
        FROM products p
        LEFT JOIN latest_prices lp ON p.id = lp.product_id
        WHERE lp.rn = 1 OR lp.rn IS NULL
        ORDER BY p.id
    """)

    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products


def get_price_history(product_id: int, limit: int = 30):
    """Get price history for a specific product."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT price, original_price, is_on_sale, checked_at
        FROM price_history
        WHERE product_id = ?
        ORDER BY checked_at DESC
        LIMIT ?
    """, (product_id, limit))

    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history


def update_product_info(product_id: int, name: str = None, image_url: str = None):
    """Update product info after first scrape."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if name:
        cursor.execute(
            "UPDATE products SET name = ? WHERE id = ?",
            (name, product_id)
        )

    if image_url:
        cursor.execute(
            "UPDATE products SET image_url = ? WHERE id = ?",
            (image_url, product_id)
        )

    conn.commit()
    conn.close()


def delete_product(product_id: int):
    """Remove a product and its price history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))

    conn.commit()
    conn.close()
    print(f"Deleted product ID: {product_id}")


if __name__ == "__main__":
    init_db()
