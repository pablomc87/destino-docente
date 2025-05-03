import os
import django
import sqlite3
import dj_database_url
from django.db import connection

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from schools.models import School, ImpartedStudy, SchoolStudy, SchoolSuggestion, SchoolEditSuggestion

def migrate_data():
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect('schools.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Define model to table mapping
    model_mapping = {
        'schools': School,
        'imparted_studies': ImpartedStudy,
        'school_studies': SchoolStudy,
        'school_suggestions': SchoolSuggestion,
        'school_edit_suggestions': SchoolEditSuggestion
    }

    # For each table
    for table_name, model in model_mapping.items():
        print(f"Migrating table: {table_name}")

        # Get all data from SQLite table
        sqlite_cursor.execute(f"SELECT * FROM {table_name};")
        rows = sqlite_cursor.fetchall()

        # Get column names
        sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [column[1] for column in sqlite_cursor.fetchall()]

        # For each row, insert into PostgreSQL
        for row in rows:
            # Create a dictionary of column names and values
            data = dict(zip(columns, row))
            
            try:
                # Create or update the object
                obj, created = model.objects.update_or_create(
                    id=data['id'],  # Assuming 'id' is the primary key
                    defaults=data
                )
                print(f"{'Created' if created else 'Updated'} {model.__name__} with id {data['id']}")
            except Exception as e:
                print(f"Error processing {table_name}: {str(e)}")
                continue

    # Close connections
    sqlite_conn.close()
    connection.close()

if __name__ == '__main__':
    print("Starting data migration...")
    migrate_data()
    print("Data migration completed!") 