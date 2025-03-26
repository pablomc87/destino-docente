from django.db import models


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
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    phone = models.CharField(blank=True, null=True, max_length=255)
    fax = models.CharField(blank=True, null=True, max_length=255)
    email = models.CharField(blank=True, null=True, max_length=255)
    website = models.CharField(blank=True, null=True, max_length=255)
    autonomous_community = models.CharField(blank=True, null=True, max_length=255)
    province = models.CharField(blank=True, null=True, max_length=255)
    country = models.CharField(blank=True, null=True, max_length=255)
    region = models.CharField(blank=True, null=True, max_length=255)
    sub_region = models.CharField(blank=True, null=True, max_length=255)
    municipality = models.CharField(blank=True, null=True, max_length=255)
    locality = models.CharField(blank=True, null=True, max_length=255)
    address = models.CharField(blank=True, null=True, max_length=255)
    postal_code = models.CharField(blank=True, null=True, max_length=255)
    nature = models.CharField(blank=True, null=True, max_length=255)
    is_concerted = models.CharField(blank=True, null=True, max_length=255)
    center_type = models.CharField(blank=True, null=True, max_length=255)
    generic_name = models.CharField(blank=True, null=True, max_length=255)
    services = models.TextField(blank=True, null=True)
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