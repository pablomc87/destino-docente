from django.db import models
from django.utils.translation import gettext_lazy as _
from typing import Any
from django.contrib.auth.models import User

NATURE_CHOICES = [
    ('Público', 'Público'),
    ('Privado', 'Privado')
]

SUGGESTION_STATUS_CHOICES = [
    ('pendiente', 'Pendiente'),
    ('aprobada', 'Aprobada'),
    ('rechazada', 'Rechazada')
]

class ImpartedStudy(models.Model):
    """Model representing a study program that can be offered by schools."""
    
    name = models.CharField(_("Name"), max_length=255)
    degree = models.CharField(_("Degree"), max_length=255, blank=True, null=True)
    family = models.CharField(_("Family"), max_length=255, blank=True, null=True)
    modality = models.CharField(_("Modality"), max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        db_table = 'imparted_studies'
        verbose_name = _("Study")
        verbose_name_plural = _("Studies")
        indexes = [
            models.Index(fields=['degree']),
            models.Index(fields=['family']),
            models.Index(fields=['modality']),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.degree or 'No degree'})"


class School(models.Model):
    """Model representing an educational institution."""

    NATURE_CHOICES = [
        ('Centro público', _('Centro público')),
        ('Centro privado', _('Centro privado'))
    ]

    # Core fields
    id = models.CharField(_("ID"), max_length=10, primary_key=True)
    name = models.CharField(_("Name"), max_length=255, db_index=True, null=True, blank=True)
    email = models.EmailField(_("Email"), null=True, blank=True)
    phone = models.CharField(_("Phone"), max_length=30, null=True, blank=True)
    fax = models.CharField(_("Fax"), max_length=30, null=True, blank=True)
    website = models.URLField(_("Website"), null=True, blank=True)

    # Location fields
    address = models.CharField(_("Address"), max_length=255, null=True, blank=True)
    postal_code = models.CharField(_("Postal code"), max_length=10, null=True, blank=True)
    municipality = models.CharField(_("Municipality"), max_length=100, db_index=True, null=True, blank=True)
    province = models.CharField(_("Province"), max_length=100, db_index=True, null=True, blank=True)
    autonomous_community = models.CharField(_("Autonomous community"), max_length=100, db_index=True, null=True, blank=True)
    region = models.CharField(_("Region"), max_length=100, null=True, blank=True)
    sub_region = models.CharField(_("Sub-region"), max_length=100, null=True, blank=True)
    locality = models.CharField(_("Locality"), max_length=100, null=True, blank=True)
    country = models.CharField(_("Country"), max_length=100, default='España', null=True, blank=True)
    
    # School characteristics
    nature = models.CharField(_("Nature"), max_length=100, choices=NATURE_CHOICES, db_index=True, null=True, blank=True)
    is_concerted = models.BooleanField(_("Is concerted"), default=False, null=True, blank=True)
    center_type = models.CharField(_("Center type"), max_length=100, db_index=True, null=True, blank=True)
    generic_name = models.CharField(_("Generic name"), max_length=255, null=True, blank=True)
    services = models.JSONField(_("Services"), default=dict, null=True, blank=True)
    
    # Geolocation
    latitude = models.DecimalField(_("Latitude"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_("Longitude"), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    
    # Relationships
    studies = models.ManyToManyField(
        ImpartedStudy,
        through='SchoolStudy',
        verbose_name=_("Studies")
    )

    class Meta:
        db_table = 'schools'
        verbose_name = _("School")
        verbose_name_plural = _("Schools")
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name or 'Unnamed'} ({self.municipality or 'No location'})"


class SchoolStudy(models.Model):
    """Through model for the many-to-many relationship between School and ImpartedStudy."""
    
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        db_column='school_id'
    )
    study = models.ForeignKey(
        ImpartedStudy,
        on_delete=models.CASCADE,
        db_column='study_id'
    )
    
    class Meta:
        db_table = 'school_studies'
        verbose_name = _("School Study")
        verbose_name_plural = _("School Studies")
        unique_together = ('school', 'study')

    def __str__(self) -> str:
        return f"{self.school.name} - {self.study.name}"


class SchoolSuggestion(models.Model):
    """Model for suggesting new schools to be added to the database."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected'))
    ]
    
    # Core fields
    name = models.CharField(_("Name"), max_length=255)
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Phone"), max_length=30)
    website = models.URLField(_("Website"), blank=True)
    
    # Location fields
    address = models.CharField(_("Address"), max_length=255)
    postal_code = models.CharField(_("Postal code"), max_length=10)
    municipality = models.CharField(_("Municipality"), max_length=100)
    province = models.CharField(_("Province"), max_length=100)
    autonomous_community = models.CharField(_("Autonomous community"), max_length=100)
    latitude = models.FloatField(_("Latitude"), null=True, blank=True)
    longitude = models.FloatField(_("Longitude"), null=True, blank=True)
    
    # School characteristics
    nature = models.CharField(_("Nature"), max_length=100, choices=NATURE_CHOICES)
    is_concerted = models.BooleanField(_("Is concerted"), default=False)
    center_type = models.CharField(_("Center type"), max_length=100)
    
    # Relationships and status
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    studies = models.ManyToManyField(ImpartedStudy)
    status = models.CharField(_("Status"), max_length=30, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(_("Notes"), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        db_table = 'school_suggestions'
        verbose_name = _("School Suggestion")
        verbose_name_plural = _("School Suggestions")
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Suggestion for {self.name} ({self.get_status_display()})"


class SchoolEditSuggestion(models.Model):
    """Model for suggesting edits to existing schools."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected'))
    ]
    
    # Core fields
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='edit_suggestions')
    name = models.CharField(_("Name"), max_length=255, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(_("Phone"), max_length=30, blank=True)
    website = models.URLField(_("Website"), blank=True)
    
    # Location fields
    address = models.CharField(_("Address"), max_length=255, blank=True)
    postal_code = models.CharField(_("Postal code"), max_length=10, blank=True)
    municipality = models.CharField(_("Municipality"), max_length=100, blank=True)
    province = models.CharField(_("Province"), max_length=100, blank=True)
    autonomous_community = models.CharField(_("Autonomous community"), max_length=100, blank=True)
    latitude = models.FloatField(_("Latitude"), null=True, blank=True)
    longitude = models.FloatField(_("Longitude"), null=True, blank=True)
    
    # Status and timestamps
    status = models.CharField(_("Status"), max_length=30, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        db_table = 'school_edit_suggestions'
        verbose_name = _("School Edit Suggestion")
        verbose_name_plural = _("School Edit Suggestions")
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Edit suggestion for {self.school.name}"


class SearchHistory(models.Model):
    """Model for tracking user search history."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    location = models.CharField(_("Location"), max_length=255)
    latitude = models.DecimalField(_("Latitude"), max_digits=9, decimal_places=6)
    longitude = models.DecimalField(_("Longitude"), max_digits=9, decimal_places=6)
    results_count = models.IntegerField(_("Number of results"), default=0)
    provinces = models.JSONField(_("Provinces"), default=list, blank=True)
    autonomous_community = models.CharField(_("Autonomous community"), max_length=100, blank=True)
    school_types = models.JSONField(_("School types"), default=list, blank=True)
    results = models.JSONField(_("Search results"), default=list, blank=True)
    timestamp = models.DateTimeField(_("Search timestamp"), auto_now_add=True)
    is_favorite = models.BooleanField(default=False)
    includes_travel_times = models.BooleanField(_("Includes travel times"), default=False,
                                              help_text="Whether this search includes travel times for the schools")

    class Meta:
        db_table = 'search_history'
        verbose_name = _("Search History")
        verbose_name_plural = _("Search History")
        ordering = ['-timestamp']

    def __str__(self) -> str:
        return f"{self.user.email} - {self.location} ({self.timestamp})"


class APICall(models.Model):
    """
    Model to track Google API calls made by the application.
    """
    API_TYPES = [
        ('directions', 'Google Directions API'),
        ('geocoding', 'Google Geocoding API'),
        ('places', 'Google Places API'),
    ]
    
    endpoint = models.CharField(max_length=255, help_text="The Google API endpoint that was called")
    api_type = models.CharField(max_length=50, choices=API_TYPES, help_text="Type of Google API being called")
    method = models.CharField(max_length=10, help_text="HTTP method used (GET, POST, etc.)")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                           help_text="User who made the call, if authenticated")
    ip_address = models.GenericIPAddressField(null=True, blank=True, 
                                            help_text="IP address of the caller")
    timestamp = models.DateTimeField(auto_now_add=True, 
                                   help_text="When the API call was made")
    response_status = models.IntegerField(help_text="HTTP status code of the response")
    response_time = models.FloatField(help_text="Response time in milliseconds")
    quota_remaining = models.IntegerField(null=True, blank=True,
                                        help_text="Remaining quota after the call")
    total_calls = models.IntegerField(null=True, blank=True,
                                    help_text="Total number of API calls in the session")
    place_selected = models.BooleanField(null=True, blank=True,
                                       help_text="Whether a place was selected in this session")
    
    class Meta:
        indexes = [
            models.Index(fields=['endpoint']),
            models.Index(fields=['api_type']),
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.api_type} - {self.method} {self.endpoint} - {self.timestamp}"