from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.template.response import TemplateResponse
from django.urls import path
from .models import School, ImpartedStudy, SchoolStudy


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'province', 'autonomous_community')
    search_fields = ('name', 'municipality', 'province', 'autonomous_community')
    list_filter = ('autonomous_community', 'province', 'nature', 'center_type')


@admin.register(ImpartedStudy)
class ImpartedStudyAdmin(admin.ModelAdmin):
    list_display = ('name', 'degree', 'family', 'modality')
    search_fields = ('name', 'degree', 'family', 'modality')
    list_filter = ('degree', 'family', 'modality')


class SchoolStudyAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'study_name')
    search_fields = ('school__name', 'study__name')
    list_filter = ('study__degree', 'study__family', 'study__modality')
    raw_id_fields = ('school', 'study')
    list_per_page = 25
    
    def school_name(self, obj):
        return obj.school.name
    school_name.short_description = 'School'
    
    def study_name(self, obj):
        return obj.study.name
    study_name.short_description = 'Study'
    
    def get_queryset(self, request):
        # Basic queryset with minimal fields to avoid the 'id' column issue
        return SchoolStudy.objects.all().select_related('school', 'study')
    
    def get_urls(self):
        # Define a custom URL pattern for the changelist view
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.custom_changelist_view), name='schools_schoolstudy_changelist'),
        ]
        return custom_urls + urls
    
    def custom_changelist_view(self, request):
        """
        Custom changelist view that uses raw SQL to avoid the 'id' column issue
        """
        # Check permissions
        if not self.has_view_permission(request):
            raise PermissionDenied
        
        # Execute raw SQL query using the schools_db connection
        with connections['schools_db'].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ss.school_id, 
                    ss.study_id,
                    s.name as school_name, 
                    i.name as study_name
                FROM 
                    school_studies ss
                JOIN 
                    schools s ON ss.school_id = s.id
                JOIN 
                    imparted_studies i ON ss.study_id = i.id
                ORDER BY
                    s.name, i.name
                LIMIT 100
            """)
            rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        school_studies = []
        for row in rows:
            school_studies.append({
                'school_id': row[0],
                'study_id': row[1],
                'school_name': row[2],
                'study_name': row[3],
                'composite_key': f"{row[0]}_{row[1]}"
            })
        
        # Render a custom template
        context = {
            'app_label': 'schools',
            'model_name': 'schoolstudy',
            'title': 'School Studies',
            'school_studies': school_studies,
            'cl': { 'result_count': len(school_studies) },  # Mock ChangeList object
            'opts': self.model._meta,
            'is_popup': False,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'has_delete_permission': self.has_delete_permission(request),
            'request': request,  # Pass the request for the template
        }
        return TemplateResponse(request, 'admin/schools/schoolstudy/change_list.html', context)
    
    def get_object(self, request, object_id, from_field=None):
        """
        Get the SchoolStudy object using the composite key
        """
        try:
            # Split the composite key
            school_id, study_id = object_id.split('_')
            # Get the object
            return self.get_queryset(request).get(school_id=school_id, study_id=study_id)
        except (ValueError, SchoolStudy.DoesNotExist):
            return None


admin.site.register(SchoolStudy, SchoolStudyAdmin)
