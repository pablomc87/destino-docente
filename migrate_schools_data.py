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

BATCH_SIZE = 100

def log_message(message):
    """Helper function to print timestamped messages."""
    print(f"[{datetime.now().isoformat()}] {message}")

def get_existing_ids(model):
    """Get set of existing IDs for a model."""
    return set(model.objects.values_list('id', flat=True))

def migrate_data():
    # Connect to the SQLite database
    sqlite_conn = sqlite3.connect('schools.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Get existing IDs
    existing_imparted_studies = get_existing_ids(ImpartedStudy)
    existing_schools = get_existing_ids(School)
    
    log_message(f"Found {len(existing_imparted_studies)} existing imparted studies")
    log_message(f"Found {len(existing_schools)} existing schools")

    # Get all imparted studies from SQLite
    sqlite_cursor.execute('SELECT * FROM imparted_studies')
    imparted_studies = sqlite_cursor.fetchall()
    log_message(f"Found {len(imparted_studies)} imparted studies in SQLite")

    # Get column names for imparted studies
    imparted_columns = [description[0] for description in sqlite_cursor.description]
    imparted_column_indices = {col: idx for idx, col in enumerate(imparted_columns)}

    # Migrate imparted studies in batches
    new_imparted_studies = 0
    for i, study in enumerate(imparted_studies, 1):
        study_id = study[imparted_column_indices['id']]
        if study_id in existing_imparted_studies:
            continue

        # Convert empty strings to None for optional fields
        degree = study[imparted_column_indices['degree']] or None
        family = study[imparted_column_indices['family']] or None
        modality = study[imparted_column_indices['modality']] or None
        
        study_data = {
            'id': study_id,
            'name': study[imparted_column_indices['name']],
            'degree': degree,
            'family': family,
            'modality': modality,
            'created_at': datetime.fromisoformat(study[imparted_column_indices['created_at']]),
            'updated_at': datetime.fromisoformat(study[imparted_column_indices['updated_at']])
        }
        
        try:
            ImpartedStudy.objects.create(**study_data)
            new_imparted_studies += 1
        except Exception as e:
            log_message(f"Error creating imparted study {study_id}: {str(e)}")

        if i % BATCH_SIZE == 0:
            log_message(f"Processed {i}/{len(imparted_studies)} imparted studies")

    log_message(f"Created {new_imparted_studies} new imparted studies")

    # Get all schools from SQLite
    sqlite_cursor.execute('SELECT * FROM schools')
    schools = sqlite_cursor.fetchall()
    log_message(f"Found {len(schools)} schools in SQLite")

    # Get column names
    columns = [description[0] for description in sqlite_cursor.description]
    column_indices = {col: idx for idx, col in enumerate(columns)}

    # Migrate schools in batches
    new_schools = 0
    for i, school in enumerate(schools, 1):
        school_id = school[column_indices['id']]
        if school_id in existing_schools:
            continue

        # Convert empty strings to None for optional fields
        fax = school[column_indices['fax']] or None
        website = school[column_indices['website']] or None
        
        # Parse JSON field
        try:
            services = json.loads(school[column_indices['services']] or '{}')
        except json.JSONDecodeError:
            services = {}
        
        school_data = {
            'id': school_id,
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
        
        try:
            School.objects.create(**school_data)
            new_schools += 1
        except Exception as e:
            log_message(f"Error creating school {school_id}: {str(e)}")

        if i % BATCH_SIZE == 0:
            log_message(f"Processed {i}/{len(schools)} schools")

    log_message(f"Created {new_schools} new schools")

    # Get all school studies from SQLite
    sqlite_cursor.execute('SELECT * FROM school_studies')
    studies = sqlite_cursor.fetchall()
    log_message(f"Found {len(studies)} school studies in SQLite")

    # Get column names for studies
    study_columns = [description[0] for description in sqlite_cursor.description]
    study_column_indices = {col: idx for idx, col in enumerate(study_columns)}

    # Migrate school studies in batches
    new_relationships = 0
    errors = 0
    for i, study in enumerate(studies, 1):
        study_data = {
            'school_id': study[study_column_indices['school_id']],
            'study_id': study[study_column_indices['study_id']]
        }
        
        # Get the corresponding School and ImpartedStudy objects
        try:
            school = School.objects.get(id=study_data['school_id'])
            imparted_study = ImpartedStudy.objects.get(id=study_data['study_id'])
            
            # Check if relationship already exists
            if not SchoolStudy.objects.filter(school=school, study=imparted_study).exists():
                SchoolStudy.objects.create(school=school, study=imparted_study)
                new_relationships += 1
        except (School.DoesNotExist, ImpartedStudy.DoesNotExist) as e:
            log_message(f"Warning: Could not create relationship for school_id={study_data['school_id']} and study_id={study_data['study_id']}: {str(e)}")
            errors += 1

        if i % BATCH_SIZE == 0:
            log_message(f"Processed {i}/{len(studies)} relationships")

    log_message(f"Created {new_relationships} new relationships")
    if errors > 0:
        log_message(f"Encountered {errors} errors while creating relationships")

    # Close SQLite connection
    sqlite_conn.close()

if __name__ == '__main__':
    log_message("Starting data migration...")
    migrate_data()
    log_message("Data migration completed successfully!") 