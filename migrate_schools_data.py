import os
import django
import sqlite3
from django.db import connection
from datetime import datetime
import json

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from schools.models import School, SchoolStudy, ImpartedStudy

def migrate_data():
    # Connect to the SQLite database
    sqlite_conn = sqlite3.connect('schools.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Get all imparted studies from SQLite
    sqlite_cursor.execute('SELECT * FROM imparted_studies')
    imparted_studies = sqlite_cursor.fetchall()

    # Get column names for imparted studies
    imparted_columns = [description[0] for description in sqlite_cursor.description]
    imparted_column_indices = {col: idx for idx, col in enumerate(imparted_columns)}

    # Migrate imparted studies
    for study in imparted_studies:
        # Convert empty strings to None for optional fields
        degree = study[imparted_column_indices['degree']] or None
        family = study[imparted_column_indices['family']] or None
        modality = study[imparted_column_indices['modality']] or None
        
        study_data = {
            'id': study[imparted_column_indices['id']],
            'name': study[imparted_column_indices['name']],
            'degree': degree,
            'family': family,
            'modality': modality,
            'created_at': datetime.fromisoformat(study[imparted_column_indices['created_at']]),
            'updated_at': datetime.fromisoformat(study[imparted_column_indices['updated_at']])
        }
        
        # Create or update imparted study in PostgreSQL
        ImpartedStudy.objects.update_or_create(
            id=study_data['id'],
            defaults=study_data
        )

    # Get all schools from SQLite
    sqlite_cursor.execute('SELECT * FROM schools')
    schools = sqlite_cursor.fetchall()

    # Get column names
    columns = [description[0] for description in sqlite_cursor.description]
    column_indices = {col: idx for idx, col in enumerate(columns)}

    # Migrate schools
    for school in schools:
        # Convert empty strings to None for optional fields
        fax = school[column_indices['fax']] or None
        website = school[column_indices['website']] or None
        
        # Parse JSON field
        services = json.loads(school[column_indices['services']] or '{}')
        
        school_data = {
            'id': school[column_indices['id']],
            'name': school[column_indices['name']],
            'email': school[column_indices['email']],
            'phone': school[column_indices['phone']],
            'fax': fax,
            'website': website,
            'address': school[column_indices['address']],
            'postal_code': school[column_indices['postal_code']],
            'municipality': school[column_indices['municipality']],
            'province': school[column_indices['province']],
            'autonomous_community': school[column_indices['autonomous_community']],
            'region': school[column_indices['region']],
            'sub_region': school[column_indices['sub_region']],
            'locality': school[column_indices['locality']],
            'country': school[column_indices['country']],
            'nature': school[column_indices['nature']],
            'is_concerted': school[column_indices['is_concerted']] == 'Yes',
            'center_type': school[column_indices['center_type']],
            'generic_name': school[column_indices['generic_name']],
            'services': services,
            'latitude': float(school[column_indices['latitude']]) if school[column_indices['latitude']] else None,
            'longitude': float(school[column_indices['longitude']]) if school[column_indices['longitude']] else None,
            'created_at': datetime.fromisoformat(school[column_indices['created_at']]),
            'updated_at': datetime.fromisoformat(school[column_indices['updated_at']])
        }
        
        # Create or update school in PostgreSQL
        School.objects.update_or_create(
            id=school_data['id'],
            defaults=school_data
        )

    # Get all school studies from SQLite
    sqlite_cursor.execute('SELECT * FROM school_studies')
    studies = sqlite_cursor.fetchall()

    # Get column names for studies
    study_columns = [description[0] for description in sqlite_cursor.description]
    study_column_indices = {col: idx for idx, col in enumerate(study_columns)}

    # Migrate school studies
    for study in studies:
        study_data = {
            'school_id': study[study_column_indices['school_id']],
            'study_id': study[study_column_indices['study_id']]
        }
        
        # Get the corresponding School and ImpartedStudy objects
        try:
            school = School.objects.get(id=study_data['school_id'])
            imparted_study = ImpartedStudy.objects.get(id=study_data['study_id'])
            
            # Create or update school study in PostgreSQL
            SchoolStudy.objects.update_or_create(
                school=school,
                study=imparted_study
            )
        except (School.DoesNotExist, ImpartedStudy.DoesNotExist) as e:
            print(f"Warning: Could not create relationship for school_id={study_data['school_id']} and study_id={study_data['study_id']}: {str(e)}")

    # Close SQLite connection
    sqlite_conn.close()

if __name__ == '__main__':
    print("Starting data migration...")
    migrate_data()
    print("Data migration completed successfully!") 