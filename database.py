import sqlite3
import os

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

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")


def save_bill(bill_no, customer, date, items, total):
    """Save a bill and its items to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO bills (bill_no, customer, date, total)
            VALUES (?, ?, ?, ?)
        """, (bill_no, customer, date, total))

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
    cursor.execute("SELECT * FROM bills ORDER BY created_at DESC")
    bills = cursor.fetchall()
    conn.close()
    return bills