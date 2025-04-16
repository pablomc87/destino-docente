class SchoolDBRouter:
    """
    A router to control all database operations on models in the
    schools application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read schools models go to schools_db.
        """
        if model._meta.app_label == 'schools':
            return 'schools_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write schools models go to schools_db.
        """
        if model._meta.app_label == 'schools':
            return 'schools_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the schools app is involved.
        """
        if obj1._meta.app_label == 'schools' or \
           obj2._meta.app_label == 'schools':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the schools app only appears in the 'schools_db'
        database.
        """
        if app_label == 'schools':
            return db == 'schools_db'
        return None 