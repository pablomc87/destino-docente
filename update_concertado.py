import os
import csv
import psycopg2
from urllib.parse import urlparse

def update_concertado_status():
    # Get database URL from environment variable
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        return

    # Parse the database URL
    url = urlparse(database_url)
    
    # Connect to the database
    conn = psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    
    try:
        cursor = conn.cursor()
        
        # Read the CSV file
        with open("school_concertado_status.csv", "r") as f:
            reader = csv.reader(f)
            updates = []
            for row in reader:
                school_id, is_concerted = row
                # Convert 'Sí'/'No' to true/false for PostgreSQL
                is_concerted_value = True if is_concerted == 'Sí' else False
                updates.append((is_concerted_value, school_id))
        
        # Update the database
        cursor.executemany(
            "UPDATE schools SET is_concerted = %s WHERE id = %s",
            updates
        )
        
        # Commit the changes
        conn.commit()
        
        # Print summary
        print(f"Updated {len(updates)} schools")
        
        # Verify some updates
        cursor.execute("SELECT id, is_concerted FROM schools WHERE id IN (%s, %s)", 
                      (updates[0][1], updates[-1][1]))
        sample = cursor.fetchall()
        print("\nSample verification:")
        for school_id, is_concerted in sample:
            print(f"School {school_id}: {'Concertado' if is_concerted else 'No concertado'}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_concertado_status()
