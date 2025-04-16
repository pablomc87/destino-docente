import sqlite3

def update_edit_suggestions_remove_created_by():
    # Connect to the database
    conn = sqlite3.connect('schools.db')
    cursor = conn.cursor()

    # Create a new table without the created_by column
    cursor.execute("""
        CREATE TABLE school_edit_suggestions_new (
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
    """)

    # Copy data from old table to new table
    cursor.execute("""
        INSERT INTO school_edit_suggestions_new (
            id, school_id, name, address, postal_code, municipality,
            province, autonomous_community, phone, email, website,
            latitude, longitude, status, created_at, updated_at
        )
        SELECT 
            id, school_id, name, address, postal_code, municipality,
            province, autonomous_community, phone, email, website,
            latitude, longitude, status, created_at, updated_at
        FROM school_edit_suggestions
    """)

    # Drop old table and rename new table
    cursor.execute("DROP TABLE school_edit_suggestions")
    cursor.execute("ALTER TABLE school_edit_suggestions_new RENAME TO school_edit_suggestions")

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print("Successfully removed created_by column from school_edit_suggestions table")

if __name__ == '__main__':
    update_edit_suggestions_remove_created_by() 