import sqlite3

def update_edit_suggestions_created_by():
    # Connect to the database
    conn = sqlite3.connect('schools.db')
    cursor = conn.cursor()

    # Add created_by column if it doesn't exist
    cursor.execute("""
        PRAGMA table_info(school_edit_suggestions)
    """)
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'created_by_id' not in columns:
        cursor.execute("""
            ALTER TABLE school_edit_suggestions
            ADD COLUMN created_by_id INTEGER REFERENCES auth_user(id)
        """)
        print("Added created_by_id column to school_edit_suggestions table")
    else:
        print("created_by_id column already exists in school_edit_suggestions table")

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_edit_suggestions_created_by() 