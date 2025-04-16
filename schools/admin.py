from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.safestring import mark_safe
from .models import School, ImpartedStudy, SchoolStudy, SchoolSuggestion, SchoolEditSuggestion


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

@admin.register(SchoolSuggestion)
class SchoolSuggestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status', 'autonomous_community', 'province')
    search_fields = ('name', 'address', 'municipality')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('school',)
        return self.readonly_fields

@admin.register(SchoolEditSuggestion)
class SchoolEditSuggestionAdmin(admin.ModelAdmin):
    list_display = ('school', 'name', 'status', 'created_at', 'get_changes_summary')
    list_filter = ('status', 'province', 'autonomous_community')
    search_fields = ('name', 'address', 'municipality', 'school__name')
    readonly_fields = ('created_at', 'updated_at', 'get_changes_comparison')
    actions = ['accept_suggestions', 'deny_suggestions']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('school', 'name', 'address', 'municipality', 
                                         'postal_code', 'province', 'autonomous_community',
                                         'email', 'phone', 'website', 'latitude', 'longitude')
        return self.readonly_fields

    def get_changes_summary(self, obj):
        """Display a summary of changes in the list view"""
        changes = []
        if obj.name and obj.name != obj.school.name:
            changes.append("Nombre")
        if obj.address and obj.address != obj.school.address:
            changes.append("Dirección")
        if obj.municipality and obj.municipality != obj.school.municipality:
            changes.append("Municipio")
        if obj.postal_code and obj.postal_code != obj.school.postal_code:
            changes.append("Código Postal")
        if obj.province and obj.province != obj.school.province:
            changes.append("Provincia")
        if obj.autonomous_community and obj.autonomous_community != obj.school.autonomous_community:
            changes.append("Comunidad Autónoma")
        if obj.email and obj.email != obj.school.email:
            changes.append("Email")
        if obj.phone and obj.phone != obj.school.phone:
            changes.append("Teléfono")
        if obj.website and obj.website != obj.school.website:
            changes.append("Web")
        if obj.latitude is not None and obj.latitude != obj.school.latitude:
            changes.append("Latitud")
        if obj.longitude is not None and obj.longitude != obj.school.longitude:
            changes.append("Longitud")
        return ", ".join(changes) if changes else "Sin cambios"
    get_changes_summary.short_description = "Cambios"

    def get_changes_comparison(self, obj):
        """Display a side-by-side comparison of current and suggested values"""
        template = """
        <table class="table">
            <thead>
                <tr>
                    <th>Campo</th>
                    <th>Valor Actual</th>
                    <th>Valor Sugerido</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
        
        rows = []
        fields = [
            ('Nombre', 'name'),
            ('Dirección', 'address'),
            ('Municipio', 'municipality'),
            ('Código Postal', 'postal_code'),
            ('Provincia', 'province'),
            ('Comunidad Autónoma', 'autonomous_community'),
            ('Email', 'email'),
            ('Teléfono', 'phone'),
            ('Web', 'website'),
            ('Latitud', 'latitude'),
            ('Longitud', 'longitude')
        ]
        
        for label, field in fields:
            current = getattr(obj.school, field)
            suggested = getattr(obj, field)
            if suggested is not None and current != suggested:  # Only show if there's a suggested value
                rows.append(f"""
                    <tr>
                        <td><strong>{label}</strong></td>
                        <td>{current}</td>
                        <td>{suggested}</td>
                    </tr>
                """)
        
        return mark_safe(template.format(rows="\n".join(rows)))
    get_changes_comparison.short_description = "Comparación de Cambios"

    @admin.action(description='Aceptar sugerencias seleccionadas')
    def accept_suggestions(self, request, queryset):
        for suggestion in queryset:
            if suggestion.status == 'pending':
                # Update the school with the suggested values
                school = suggestion.school
                for field in ['name', 'address', 'municipality', 'postal_code', 
                            'province', 'autonomous_community', 'email', 'phone', 
                            'website', 'latitude', 'longitude']:
                    suggested_value = getattr(suggestion, field)
                    if suggested_value is not None:  # Only update if there's a suggested value
                        setattr(school, field, suggested_value)
                school.save()
                suggestion.status = 'accepted'
                suggestion.save()
        self.message_user(request, f"{queryset.count()} sugerencias aceptadas correctamente.")

    @admin.action(description='Denegar sugerencias seleccionadas')
    def deny_suggestions(self, request, queryset):
        queryset.update(status='denied')
        self.message_user(request, f"{queryset.count()} sugerencias denegadas correctamente.")

    def has_add_permission(self, request):
        return False  # Disable adding new suggestions through admin
