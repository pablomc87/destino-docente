from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import School, ImpartedStudy, SchoolStudy, SchoolSuggestion, SchoolEditSuggestion


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'province', 'autonomous_community', 'nature', 'center_type')
    list_filter = ('autonomous_community', 'province', 'nature', 'center_type', 'is_concerted')
    search_fields = ('name', 'municipality', 'province', 'autonomous_community', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Core Information'), {
            'fields': ('id', 'name', 'email', 'phone', 'fax', 'website')
        }),
        (_('Location'), {
            'fields': ('address', 'postal_code', 'municipality', 'province', 
                      'autonomous_community', 'region', 'sub_region', 'locality', 'country')
        }),
        (_('School Details'), {
            'fields': ('nature', 'is_concerted', 'center_type', 'generic_name', 'services')
        }),
        (_('Geolocation'), {
            'fields': ('latitude', 'longitude')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ImpartedStudy)
class ImpartedStudyAdmin(admin.ModelAdmin):
    list_display = ('name', 'degree', 'family', 'modality')
    list_filter = ('degree', 'family', 'modality')
    search_fields = ('name', 'degree', 'family', 'modality')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'degree', 'family', 'modality')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(SchoolStudy)
class SchoolStudyAdmin(admin.ModelAdmin):
    list_display = ('school', 'study')
    list_filter = ('study__degree', 'study__family', 'study__modality')
    search_fields = ('school__name', 'study__name')
    autocomplete_fields = ['school', 'study']


@admin.register(SchoolSuggestion)
class SchoolSuggestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'province', 'status', 'created_at')
    list_filter = ('status', 'autonomous_community', 'province', 'nature', 'is_concerted')
    search_fields = ('name', 'municipality', 'province', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Core Information'), {
            'fields': ('name', 'email', 'phone', 'website')
        }),
        (_('Location'), {
            'fields': ('address', 'postal_code', 'municipality', 'province', 
                      'autonomous_community', 'latitude', 'longitude')
        }),
        (_('School Details'), {
            'fields': ('nature', 'is_concerted', 'center_type')
        }),
        (_('Relationships'), {
            'fields': ('school', 'studies')
        }),
        (_('Status'), {
            'fields': ('status', 'notes')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(SchoolEditSuggestion)
class SchoolEditSuggestionAdmin(admin.ModelAdmin):
    list_display = ('school', 'status', 'created_at', 'get_changes_summary')
    list_filter = ('status', 'created_at')
    search_fields = ('school__name', 'name', 'municipality')
    readonly_fields = ('created_at', 'updated_at', 'get_changes_comparison')
    actions = ['accept_suggestions', 'reject_suggestions']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('school',)
        return self.readonly_fields

    def get_changes_summary(self, obj):
        """Display a summary of changes in the list view"""
        changes = []
        fields_to_check = [
            ('name', _('Name')),
            ('address', _('Address')),
            ('municipality', _('Municipality')),
            ('postal_code', _('Postal Code')),
            ('province', _('Province')),
            ('autonomous_community', _('Autonomous Community')),
            ('email', _('Email')),
            ('phone', _('Phone')),
            ('website', _('Website')),
            ('latitude', _('Latitude')),
            ('longitude', _('Longitude')),
        ]
        
        for field, label in fields_to_check:
            suggested = getattr(obj, field)
            current = getattr(obj.school, field)
            if suggested and suggested != current:
                changes.append(str(label))
        
        return ', '.join(changes) if changes else _('No changes')
    get_changes_summary.short_description = _('Changes')

    def get_changes_comparison(self, obj):
        """Display a side-by-side comparison of current and suggested values"""
        template = '''
        <style>
            .changes-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            .changes-table th, .changes-table td { 
                padding: 8px; 
                border: 1px solid #ddd; 
                text-align: left; 
            }
            .changes-table th { background-color: #f5f5f5; }
            .changes-row:nth-child(even) { background-color: #f9f9f9; }
            .different { background-color: #fff3cd; }
        </style>
        <table class="changes-table">
            <thead>
                <tr>
                    <th>{field}</th>
                    <th>{current}</th>
                    <th>{suggested}</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        '''.format(
            field=_('Field'),
            current=_('Current Value'),
            suggested=_('Suggested Value'),
            rows=self._get_comparison_rows(obj)
        )
        return mark_safe(template)
    get_changes_comparison.short_description = _('Changes Comparison')

    def _get_comparison_rows(self, obj):
        fields_to_compare = [
            ('name', _('Name')),
            ('address', _('Address')),
            ('municipality', _('Municipality')),
            ('postal_code', _('Postal Code')),
            ('province', _('Province')),
            ('autonomous_community', _('Autonomous Community')),
            ('email', _('Email')),
            ('phone', _('Phone')),
            ('website', _('Website')),
            ('latitude', _('Latitude')),
            ('longitude', _('Longitude')),
        ]
        
        rows = []
        for field, label in fields_to_compare:
            suggested = getattr(obj, field)
            current = getattr(obj.school, field)
            if suggested and suggested != current:
                rows.append(
                    '<tr class="changes-row different">'
                    f'<td><strong>{label}</strong></td>'
                    f'<td>{current or "-"}</td>'
                    f'<td>{suggested or "-"}</td>'
                    '</tr>'
                )
        return '\n'.join(rows)

    @admin.action(description=_('Accept selected suggestions'))
    def accept_suggestions(self, request, queryset):
        for suggestion in queryset.filter(status='pending'):
            school = suggestion.school
            fields_to_update = [
                'name', 'address', 'municipality', 'postal_code', 'province',
                'autonomous_community', 'email', 'phone', 'website', 'latitude', 'longitude'
            ]
            
            for field in fields_to_update:
                suggested_value = getattr(suggestion, field)
                if suggested_value:
                    setattr(school, field, suggested_value)
            
            school.save()
            suggestion.status = 'approved'
            suggestion.save()

        self.message_user(request, _('%(count)d suggestions were successfully accepted.') % {
            'count': queryset.count()
        })

    @admin.action(description=_('Reject selected suggestions'))
    def reject_suggestions(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, _('%(count)d suggestions were successfully rejected.') % {
            'count': updated
        })
