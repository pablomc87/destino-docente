import sqlite3
import os
from datetime import datetime, timezone

def update_edit_suggestions():
    # Create a new database
    conn = sqlite3.connect('schools_new.db')
    cursor = conn.cursor()

    # Create the updated school_edit_suggestions table
    cursor.execute('''
    CREATE TABLE school_edit_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id TEXT NOT NULL,
        name TEXT,
        address TEXT,
        postal_code TEXT,
        municipality TEXT,
        province TEXT,
        autonomous_community TEXT,
        phone TEXT,
        email TEXT,
        website TEXT,
        latitude REAL,
        longitude REAL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (school_id) REFERENCES schools(id)
    )
    ''')

    # Copy existing tables from the old database
    old_conn = sqlite3.connect('schools.db')
    old_cursor = old_conn.cursor()

    # Get list of existing tables
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in old_cursor.fetchall() 
              if row[0] != 'school_edit_suggestions']

    # Copy data from each table
    for table in tables:
        # Get table structure
        old_cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in old_cursor.fetchall()]
        columns_str = ', '.join(columns)
        
        # Create table in new database
        old_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        create_table_sql = old_cursor.fetchone()[0]
        cursor.execute(create_table_sql)
        
        # Copy data
        old_cursor.execute(f"SELECT {columns_str} FROM {table}")
        rows = old_cursor.fetchall()
        if rows:
            placeholders = ', '.join(['?' for _ in columns])
            cursor.executemany(f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})", rows)

    # Copy data from old school_edit_suggestions table
    old_cursor.execute("""
        SELECT id, school_id, name, address, postal_code, municipality,
               province, autonomous_community, phone, email, website,
               status, created_at, updated_at
        FROM school_edit_suggestions
    """)
    rows = old_cursor.fetchall()
    if rows:
        cursor.executemany("""
            INSERT INTO school_edit_suggestions (
                id, school_id, name, address, postal_code, municipality,
                province, autonomous_community, phone, email, website,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

    # Commit changes and close connections
    conn.commit()
    conn.close()
    old_conn.close()

    # Replace old database with new one
    os.remove('schools.db')
    os.rename('schools_new.db', 'schools.db')

    print("Successfully updated school_edit_suggestions table with latitude and longitude columns")

if __name__ == '__main__':
    update_edit_suggestions() 