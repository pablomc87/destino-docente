import os
import django
import sqlite3
import dj_database_url
from django.db import connection

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from schools.models import *  # Import all your models

def migrate_data():
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect('schools.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Get all tables from SQLite
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = sqlite_cursor.fetchall()

    # For each table
    for table in tables:
        table_name = table[0]
        if table_name.startswith('sqlite_') or table_name == 'django_migrations':
            continue

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
            
            # Get the model class
            model_name = ''.join(word.capitalize() for word in table_name.split('_'))
            try:
                model = globals()[model_name]
                
                # Create or update the object
                obj, created = model.objects.update_or_create(
                    id=data['id'],  # Assuming 'id' is the primary key
                    defaults=data
                )
                print(f"{'Created' if created else 'Updated'} {model_name} with id {data['id']}")
            except KeyError:
                print(f"Could not find model for table {table_name}")
                continue
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