import os
import sqlite3

# Define the database file name
DB_FILE = "company_sales.db"

MOCK_DATA_SQL_SCRIPT = """
-- Customers Table
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    company_name TEXT,
    tier TEXT, -- 'Enterprise', 'Mid-Market', 'SMB'
    region TEXT
);

-- Orders Table
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE,
    revenue REAL,
    product_category TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

-- Mock Data Insertions
INSERT INTO customers VALUES (1, 'TechCorp Solutions', 'Enterprise', 'North'),
                             (2, 'Global Logistics Inc', 'Enterprise', 'West'),
                             (3, 'Alpha Retail', 'Mid-Market', 'North'),
                             (4, 'Beta Health', 'SMB', 'South');

INSERT INTO orders VALUES (101, 1, '2026-01-15', 50000.0, 'SaaS Subscription'),
                           (102, 2, '2026-02-10', 120000.0, 'On-Prem License'),
                           (103, 1, '2026-03-05', 45000.0, 'Professional Services'),
                           (104, 3, '2026-01-22', 15000.0, 'SaaS Subscription'),
                           (105, 4, '2026-03-20', 5000.0, 'SaaS Subscription');
"""


def setup_database():
    try:
        # Connect to the database. If the file doesn't exist, it will be created.
        print(f"Connecting to database: {DB_FILE}")
        conn = sqlite3.connect(DB_FILE)

        # Create a cursor object to execute SQL commands
        cursor = conn.cursor()

        # executescript() allows running multiple SQL statements separated by semicolons
        print("Executing SQL script...")
        cursor.executescript(MOCK_DATA_SQL_SCRIPT)

        # Commit the changes to the database
        conn.commit()
        print("Database initialized and mock data inserted successfully!")

        # Verify the data was inserted
        print("\nVerifying data inside 'customers' table:")
        cursor.execute("SELECT * FROM customers;")
        rows = cursor.fetchall()

        for row in rows:
            print(
                f"Customer ID: {row[0]} | Company Name: {row[1]} | Tier: {row[2]} | Region: {row[3]}"
            )

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        # Always ensure the connection is closed
        if conn:
            conn.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    # Cleaning up old DB file, to have a fresh start at each run
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    setup_database()
