from rest_framework import serializers
from .models import School, ImpartedStudy, SchoolSuggestion, SchoolEditSuggestion

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
            'website', 'is_concerted', 'generic_name', 'services', 'studies',
            'latitude', 'longitude'
        ]

class SchoolSuggestionSerializer(serializers.ModelSerializer):
    studies = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    is_concerted = serializers.BooleanField(required=False, default=False)
    
    class Meta:
        model = SchoolSuggestion
        fields = [
            'id', 'name', 'email', 'phone', 'website', 'address', 'postal_code',
            'municipality', 'province', 'autonomous_community', 'latitude', 'longitude',
            'nature', 'is_concerted', 'center_type', 'school', 'notes', 'studies',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ('status', 'created_at', 'updated_at', 'id')

    def validate_latitude(self, value):
        if value is not None:
            try:
                value = float(value)
                if not -90 <= value <= 90:
                    raise serializers.ValidationError("Latitude must be between -90 and 90 degrees")
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid latitude value")
        return value

    def validate_longitude(self, value):
        if value is not None:
            try:
                value = float(value)
                if not -180 <= value <= 180:
                    raise serializers.ValidationError("Longitude must be between -180 and 180 degrees")
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid longitude value")
        return value

    def create(self, validated_data):
        studies = validated_data.pop('studies', [])
        instance = super().create(validated_data)

        if studies:
            for study_name in studies:
                study = ImpartedStudy.objects.filter(name=study_name).first()
                if study:
                    instance.studies.add(study)
                else:
                    study = ImpartedStudy.objects.create(name=study_name)
                    instance.studies.add(study)

        return instance

class SchoolEditSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for school edit suggestions"""
    class Meta:
        model = SchoolEditSuggestion
        fields = [
            'id', 'school', 'name', 'address', 'postal_code', 'municipality',
            'province', 'autonomous_community', 'phone', 'email', 'website',
            'latitude', 'longitude', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ('status', 'created_at', 'updated_at')

    def validate_latitude(self, value):
        if value is not None:
            try:
                value = float(value)
                if not -90 <= value <= 90:
                    raise serializers.ValidationError("Latitude must be between -90 and 90 degrees")
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid latitude value")
        return value

    def validate_longitude(self, value):
        if value is not None:
            try:
                value = float(value)
                if not -180 <= value <= 180:
                    raise serializers.ValidationError("Longitude must be between -180 and 180 degrees")
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid longitude value")
        return value