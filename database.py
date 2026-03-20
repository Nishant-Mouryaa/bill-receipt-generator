import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "database/receipts.db"


def init_db():
    """Initialize the database and create tables."""
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Bills Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no     TEXT UNIQUE NOT NULL,
            customer    TEXT NOT NULL,
            date        TEXT NOT NULL,
            total       REAL NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create Bill Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no     TEXT NOT NULL,
            item_name   TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            price       REAL NOT NULL,
            subtotal    REAL NOT NULL,
            FOREIGN KEY (bill_no) REFERENCES bills(bill_no)
        )
    """)

    # Add currency column if it doesn't exist
    cursor.execute("PRAGMA table_info(bills)")
    columns = [col[1] for col in cursor.fetchall()]
    if "currency" not in columns:
        cursor.execute("ALTER TABLE bills ADD COLUMN currency TEXT DEFAULT 'USD'")

    conn.commit()
    conn.close()


def save_bill(bill_no, customer, date, items, total, currency="USD"):
    """Save a bill and its items to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO bills (bill_no, customer, date, total, currency)
            VALUES (?, ?, ?, ?, ?)
        """, (bill_no, customer, date, total, currency))

        for item in items:
            cursor.execute("""
                INSERT INTO bill_items (bill_no, item_name, quantity, price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (bill_no, item["name"], item["qty"], item["price"], item["subtotal"]))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        print(f"❌ Bill {bill_no} already exists!")
        return False

    finally:
        conn.close()


def fetch_all_bills():
    """Fetch all bills from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, bill_no, customer, date, total, created_at, 
               COALESCE(currency, 'USD') as currency 
        FROM bills 
        ORDER BY created_at DESC
    """)
    bills = cursor.fetchall()
    conn.close()
    return bills


def fetch_bill_items(bill_no):
    """Fetch items for a specific bill."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT item_name, quantity, price, subtotal 
        FROM bill_items 
        WHERE bill_no = ?
    """, (bill_no,))
    items = cursor.fetchall()
    conn.close()
    return items


def fetch_bill_by_id(bill_id):
    """Fetch a single bill by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, bill_no, customer, date, total, created_at,
               COALESCE(currency, 'USD') as currency
        FROM bills 
        WHERE id = ?
    """, (bill_id,))
    bill = cursor.fetchone()
    conn.close()
    return bill


def delete_bill(bill_no):
    """Delete a bill and its items."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM bill_items WHERE bill_no = ?", (bill_no,))
        cursor.execute("DELETE FROM bills WHERE bill_no = ?", (bill_no,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting bill: {e}")
        return False
    finally:
        conn.close()


# Analytics functions
def get_total_revenue():
    """Get total revenue from all bills."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM bills")
    total = cursor.fetchone()[0]
    conn.close()
    return total


def get_total_bills_count():
    """Get total number of bills."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bills")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_average_bill_amount():
    """Get average bill amount."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(AVG(total), 0) FROM bills")
    avg = cursor.fetchone()[0]
    conn.close()
    return avg


def get_top_customers(limit=5):
    """Get top customers by total spending."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT customer, SUM(total) as total_spent, COUNT(*) as bill_count
        FROM bills
        GROUP BY customer
        ORDER BY total_spent DESC
        LIMIT ?
    """, (limit,))
    customers = cursor.fetchall()
    conn.close()
    return customers


def get_top_items(limit=10):
    """Get top selling items by quantity."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT item_name, SUM(quantity) as total_qty, SUM(subtotal) as total_revenue
        FROM bill_items
        GROUP BY item_name
        ORDER BY total_qty DESC
        LIMIT ?
    """, (limit,))
    items = cursor.fetchall()
    conn.close()
    return items


def get_revenue_by_date(days=30):
    """Get daily revenue for the last N days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    cursor.execute("""
        SELECT DATE(date) as bill_date, SUM(total) as daily_total
        FROM bills
        WHERE DATE(date) >= DATE(?)
        GROUP BY DATE(date)
        ORDER BY bill_date
    """, (start_date.strftime("%Y-%m-%d"),))
    
    data = cursor.fetchall()
    conn.close()
    return data


def get_monthly_revenue(months=12):
    """Get monthly revenue for the last N months."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(total) as monthly_total
        FROM bills
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        LIMIT ?
    """, (months,))
    data = cursor.fetchall()
    conn.close()
    return list(reversed(data))


def get_bills_by_date_range(start_date, end_date):
    """Get bills within a date range."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, bill_no, customer, date, total, created_at,
               COALESCE(currency, 'USD') as currency
        FROM bills
        WHERE DATE(date) BETWEEN DATE(?) AND DATE(?)
        ORDER BY date DESC
    """, (start_date, end_date))
    bills = cursor.fetchall()
    conn.close()
    return bills


def search_bills(search_term):
    """Search bills by customer name or bill number."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    search_pattern = f"%{search_term}%"
    cursor.execute("""
        SELECT id, bill_no, customer, date, total, created_at,
               COALESCE(currency, 'USD') as currency
        FROM bills
        WHERE customer LIKE ? OR bill_no LIKE ?
        ORDER BY created_at DESC
    """, (search_pattern, search_pattern))
    bills = cursor.fetchall()
    conn.close()
    return bills