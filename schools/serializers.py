from rest_framework import serializers
from .models import School, ImpartedStudy

class StudySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpartedStudy
        fields = ['id', 'name', 'degree', 'family', 'modality']

class SchoolSerializer(serializers.ModelSerializer):
    studies = StudySerializer(many=True, read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'name', 'municipality', 'province', 'autonomous_community',
            'center_type', 'nature', 'address', 'postal_code', 'phone', 'email',
            'website', 'is_concerted', 'generic_name', 'services', 'studies'
        ] 