from django.db import models
from django.db.models import Q
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
    id = models.AutoField(primary_key=True)
    degree = models.CharField(blank=True, null=True, max_length=255)
    family = models.CharField(blank=True, null=True, max_length=255)
    name = models.CharField(max_length=255)
    modality = models.CharField(blank=True, null=True, max_length=255)
    created_at = models.CharField(max_length=255)
    updated_at = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'imparted_studies'
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'
        indexes = [
            models.Index(fields=['degree']),
            models.Index(fields=['family']),
            models.Index(fields=['modality']),
        ]

    def __str__(self):
        return f"{self.name} ({self.degree})"


class School(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    fax = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField()
    autonomous_community = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    sub_region = models.CharField(max_length=100)
    municipality = models.CharField(max_length=100)
    locality = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=10)
    nature = models.CharField(max_length=50)
    is_concerted = models.BooleanField()
    center_type = models.CharField(max_length=50)
    generic_name = models.CharField(max_length=255)
    services = models.JSONField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.CharField(max_length=255)
    updated_at = models.CharField(max_length=255)
    studies = models.ManyToManyField(ImpartedStudy, through='SchoolStudy')

    class Meta:
        managed = False
        db_table = 'schools'
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        indexes = [
            models.Index(fields=['municipality']),
            models.Index(fields=['province']),
            models.Index(fields=['autonomous_community']),
            models.Index(fields=['nature']),
            models.Index(fields=['center_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.municipality})"


class SchoolStudy(models.Model):
    # Explicitly define both fields as primary key components
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_column='school_id', primary_key=True)
    study = models.ForeignKey(ImpartedStudy, on_delete=models.CASCADE, db_column='study_id')
    
    class Meta:
        managed = False
        db_table = 'school_studies'
        verbose_name = 'School Study'
        verbose_name_plural = 'School Studies'
        unique_together = ('school', 'study')
    
    def __str__(self):
        return f"{self.school.name} - {self.study.name}"
    
    @property
    def composite_key(self):
        """Property that combines school_id and study_id to create a unique identifier."""
        return f"{self.school_id}_{self.study_id}"


class SchoolSuggestion(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=10)
    municipality = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    autonomous_community = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    nature = models.CharField(max_length=50, choices=NATURE_CHOICES)
    is_concerted = models.BooleanField(default=False)
    center_type = models.CharField(max_length=100)
    studies = models.ManyToManyField(ImpartedStudy, db_table='school_suggestion_studies')
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'school_suggestions'
        verbose_name = 'School Suggestion'
        verbose_name_plural = 'School Suggestions'
    
    def __str__(self):
        return f"Suggestion for {self.name} ({self.status})"


class SchoolEditSuggestion(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='edit_suggestions')
    name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    autonomous_community = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SUGGESTION_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'school_edit_suggestions'
        managed = False

    def __str__(self):
        return f"Edit suggestion for {self.school.name}"