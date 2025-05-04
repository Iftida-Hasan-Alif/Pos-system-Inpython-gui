import sqlite3
from datetime import datetime
import os
import sys
import time
from contextlib import contextmanager
from decimal import Decimal

DATABASE = 'pos_system.db'

def resource_path(relative_path):
    """Get absolute path to resource for both dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

@contextmanager
def get_db_connection():
    """Context manager for database connections with proper timeout handling"""
    conn = sqlite3.connect(resource_path(DATABASE), timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
    conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database with proper settings"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if database needs initialization
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
            needs_init = cursor.fetchone() is None
            
            if needs_init:
                # Products table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        buy_price REAL NOT NULL,
                        sell_price REAL NOT NULL,
                        quantity INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Customers table with email
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS customers (
                        phone TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT,
                        address TEXT,
                        due REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Sales table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_phone TEXT,
                        total_amount REAL NOT NULL,
                        discount REAL DEFAULT 0,
                        amount_paid REAL NOT NULL,
                        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_phone) REFERENCES customers(phone)
                    )
                ''')
                
                # Sale items table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sale_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sale_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER NOT NULL,
                        unit_price REAL NOT NULL,
                        FOREIGN KEY (sale_id) REFERENCES sales(id),
                        FOREIGN KEY (product_id) REFERENCES products(id)
                    )
                ''')
                
                # Payments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_phone TEXT,
                        amount REAL NOT NULL,
                        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_phone) REFERENCES customers(phone)
                    )
                ''')
                
                # Add version table for future migrations
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS db_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute("INSERT INTO db_version (version) VALUES (1)")
                
                conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Database initialization failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during initialization: {str(e)}")

# [Rest of your database functions remain the same]
def with_retry(max_retries=3, delay=0.5):
    """Decorator for adding retry logic to database operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e) and attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise
        return wrapper
    return decorator

# Product functions
@with_retry()
def add_product(name, description, buy_price, sell_price, quantity):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO products (name, description, buy_price, sell_price, quantity)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, float(buy_price), float(sell_price), int(quantity)))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Product with this name already exists")

@with_retry()
def update_product(product_id, name, description, buy_price, sell_price, quantity):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET name=?, description=?, buy_price=?, sell_price=?, quantity=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (name, description, float(buy_price), float(sell_price), int(quantity), product_id))
        conn.commit()

@with_retry()
def get_all_products():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, description, buy_price, sell_price, quantity
            FROM products
            ORDER BY name
        ''')
        return cursor.fetchall()

@with_retry()
def get_product_by_name(name):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, description, buy_price, sell_price, quantity 
            FROM products WHERE name=?
        ''', (name,))
        return cursor.fetchone()

@with_retry()
def search_products(query):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, description, sell_price, quantity 
            FROM products 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
        ''', (f'%{query}%', f'%{query}%'))
        return cursor.fetchall()

# Customer functions
@with_retry()
def add_customer(phone, name, email=None, address=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO customers (phone, name, email, address)
            VALUES (?, ?, ?, ?)
        ''', (phone, name, email, address))
        conn.commit()

@with_retry()
def get_customer(phone):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT phone, name, email, address FROM customers WHERE phone=?
        ''', (phone,))
        return cursor.fetchone()

@with_retry()
def get_all_customers():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT phone, name, email, address FROM customers ORDER BY name
        ''')
        return cursor.fetchall()

@with_retry()
def search_customers(query):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT phone, name, email, address 
            FROM customers 
            WHERE phone LIKE ? OR name LIKE ? OR email LIKE ?
            ORDER BY name
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        return cursor.fetchall()

@with_retry()
def get_customer_due(phone):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total sales amount
        cursor.execute('''
            SELECT COALESCE(SUM(total_amount - amount_paid), 0) 
            FROM sales 
            WHERE customer_phone=?
        ''', (phone,))
        sales_due = cursor.fetchone()[0]
        
        # Get total payments
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) 
            FROM payments 
            WHERE customer_phone=?
        ''', (phone,))
        payments = cursor.fetchone()[0]
        
        return Decimal(str(sales_due - payments))

# Sales functions
@with_retry(max_retries=5, delay=1)
def record_sale(customer_phone, items, discount, amount_paid):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            conn.execute("BEGIN IMMEDIATE TRANSACTION")
            
            # Calculate totals
            subtotal = sum(Decimal(str(qty)) * Decimal(str(price)) for _, qty, price in items)
            total_amount = subtotal - Decimal(str(discount))
            
            # Insert sale record
            cursor.execute('''
                INSERT INTO sales (customer_phone, total_amount, discount, amount_paid)
                VALUES (?, ?, ?, ?)
            ''', (customer_phone, float(total_amount), float(discount), float(amount_paid)))
            sale_id = cursor.lastrowid
            
            # Insert sale items and update product quantities
            for product_name, qty, price in items:
                product = get_product_by_name(product_name)
                if product:
                    cursor.execute('''
                        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                        VALUES (?, ?, ?, ?)
                    ''', (sale_id, product[0], qty, float(price)))
                    
                    # Update product quantity
                    cursor.execute('''
                        UPDATE products 
                        SET quantity = quantity - ? 
                        WHERE id=?
                    ''', (qty, product[0]))

            # Update customer's due
            cursor.execute('''
                UPDATE customers SET due = due + ? - ? WHERE phone = ?
            ''', (float(total_amount), float(amount_paid), customer_phone))

            conn.commit()
            return sale_id
        except Exception as e:
            conn.rollback()
            raise e

# Payment functions
@with_retry()
def record_payment(customer_phone, amount):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (customer_phone, amount)
            VALUES (?, ?)
        ''', (customer_phone, float(amount)))
        conn.commit()

@with_retry()
def get_payment_history():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.payment_date, c.name, p.amount 
            FROM payments p
            JOIN customers c ON p.customer_phone = c.phone
            ORDER BY p.payment_date DESC
        ''')
        return cursor.fetchall()