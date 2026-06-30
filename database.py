"""
GET YOUR PLUS — Database Layer
SQLite3 setup, schema creation, and CRUD helpers.
"""

import sqlite3
import os
from datetime import datetime
from config import DB_PATH
from utils.orderid import generate_order_id
from utils.helpers import calculate_warranty_expiry


def get_connection():
    """Get a database connection with row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            joined_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT NOT NULL,
            description       TEXT DEFAULT '',
            price             REAL NOT NULL,
            stock             INTEGER NOT NULL DEFAULT 0,
            warranty_days     INTEGER DEFAULT 0,
            warranty_details  TEXT DEFAULT '',
            image_path        TEXT DEFAULT '',
            is_active         INTEGER NOT NULL DEFAULT 1,
            created_at        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id          TEXT UNIQUE NOT NULL,
            chat_id           INTEGER NOT NULL,
            product_id        INTEGER NOT NULL,
            product_name      TEXT NOT NULL,
            price             REAL NOT NULL,
            quantity          INTEGER NOT NULL DEFAULT 1,
            warranty_expiry   TEXT,
            warranty_details  TEXT DEFAULT '',
            status            TEXT NOT NULL DEFAULT 'pending',
            created_at        TEXT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_chat_id ON orders(chat_id);
        CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
    """)

    conn.commit()
    conn.close()


# ─── User CRUD ───────────────────────────────────────────────────────

def upsert_user(chat_id: int, username: str = None, first_name: str = None):
    """Insert or update a user."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO users (chat_id, username, first_name, joined_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(chat_id) DO UPDATE SET
             username = COALESCE(excluded.username, users.username),
             first_name = COALESCE(excluded.first_name, users.first_name)
        """,
        (chat_id, username, first_name, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_users():
    """Get all registered users."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
    conn.close()
    return rows


def get_user_count():
    """Get total user count."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count


# ─── Product CRUD ────────────────────────────────────────────────────

def add_product(name, description, price, stock, warranty_days, warranty_details, image_path):
    """Add a new product. Returns the product ID."""
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO products 
           (name, description, price, stock, warranty_days, warranty_details, image_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, description, price, stock, warranty_days, warranty_details, image_path,
         datetime.now().isoformat()),
    )
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id


def get_product(product_id: int):
    """Get a single product by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return row


def get_active_products():
    """Get all active products."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_all_products():
    """Get all products (including inactive)."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def update_product_field(product_id: int, field: str, value):
    """Update a single field of a product."""
    allowed = {
        "name", "description", "price", "stock", "warranty_days",
        "warranty_details", "image_path", "is_active",
    }
    if field not in allowed:
        raise ValueError(f"Invalid field: {field}")
    
    conn = get_connection()
    conn.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
    conn.commit()
    conn.close()


def delete_product(product_id: int):
    """Delete a product."""
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


def toggle_product_active(product_id: int):
    """Toggle product active status. Returns new status."""
    conn = get_connection()
    current = conn.execute(
        "SELECT is_active FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if current is None:
        conn.close()
        return None
    new_status = 0 if current["is_active"] else 1
    conn.execute(
        "UPDATE products SET is_active = ? WHERE id = ?", (new_status, product_id)
    )
    conn.commit()
    conn.close()
    return new_status


# ─── Order CRUD ──────────────────────────────────────────────────────

def create_order(chat_id: int, product_id: int):
    """
    Create a new order. Decrements stock.
    Returns (order_id, order_dict) or (None, error_message).
    """
    conn = get_connection()
    
    # Get product
    product = conn.execute(
        "SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,)
    ).fetchone()
    
    if not product:
        conn.close()
        return None, "Product not found or inactive."
    
    if product["stock"] <= 0:
        conn.close()
        return None, "Sorry, this product is out of stock! 😔"
    
    # Generate unique order ID
    existing = set(
        row[0] for row in conn.execute("SELECT order_id FROM orders").fetchall()
    )
    order_id = generate_order_id(existing)
    
    # Calculate warranty
    warranty_expiry = calculate_warranty_expiry(product["warranty_days"])
    
    now = datetime.now().isoformat()
    
    # Create order and decrement stock
    conn.execute(
        """INSERT INTO orders 
           (order_id, chat_id, product_id, product_name, price, quantity,
            warranty_expiry, warranty_details, status, created_at)
           VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'pending', ?)""",
        (order_id, chat_id, product_id, product["name"], product["price"],
         warranty_expiry, product["warranty_details"], now),
    )
    conn.execute(
        "UPDATE products SET stock = stock - 1 WHERE id = ?", (product_id,)
    )
    conn.commit()
    
    # Build order dict
    order = {
        "order_id": order_id,
        "product_name": product["name"],
        "price": product["price"],
        "warranty_expiry": warranty_expiry,
        "warranty_details": product["warranty_details"],
        "warranty_days": product["warranty_days"],
        "created_at": now,
        "status": "pending",
    }
    
    conn.close()
    return order_id, order


def get_user_orders(chat_id: int):
    """Get all orders for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orders WHERE chat_id = ? ORDER BY created_at DESC",
        (chat_id,),
    ).fetchall()
    conn.close()
    return rows


def get_order_by_id(order_id: str):
    """Get a single order by order_id."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return row


def get_all_orders(status_filter: str = None):
    """Get all orders, optionally filtered by status."""
    conn = get_connection()
    if status_filter:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC",
            (status_filter,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return rows


def update_order_status(order_id: str, new_status: str):
    """Update order status."""
    allowed = {"pending", "confirmed", "shipped", "completed"}
    if new_status not in allowed:
        raise ValueError(f"Invalid status: {new_status}")
    
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id)
    )
    conn.commit()
    conn.close()
