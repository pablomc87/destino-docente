from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import Q
import math
import requests
from datetime import datetime, timedelta
from django.conf import settings
from .models import School, ImpartedStudy
from .serializers import SchoolSerializer, StudySerializer
from rest_framework.views import APIView
from rest_framework import status
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from functools import lru_cache
import logging
import googlemaps
from django.http import JsonResponse
from django.views import View
import json
from django.core.serializers import serialize
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import Lower
from django.core.exceptions import ValidationError
from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import Cast

api_key = settings.GOOGLE_MAPS_API_KEY

# Create your views here.

def index(request):
    """Render the main search page"""
    return render(request, 'schools/index.html')

def school_detail(request, pk):
    """Render the school detail page"""
    return render(request, 'schools/school_detail.html')

class SchoolListView(generics.ListAPIView):
    """List all schools"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def get_queryset(self):
        return School.objects.all()

class SchoolDetailView(generics.RetrieveAPIView):
    """Get details of a specific school"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def get_object(self):
        return School.objects.get(id=self.kwargs['pk'])

class SchoolSearchView(generics.ListAPIView):
    """Search schools by name, municipality, or province"""
    serializer_class = SchoolSerializer

    def get_queryset(self):
        query = self.request.query_params.get('name', '')
        if not query:
            return School.objects.none()
        
        return School.objects.filter(
            Q(name__icontains=query) |
            Q(municipality__icontains=query) |
            Q(province__icontains=query)
        )[:50]  # Limit results to 50 schools

class StudyListView(generics.ListAPIView):
    """List all studies"""
    queryset = ImpartedStudy.objects.all()
    serializer_class = StudySerializer

    def get_queryset(self):
        return ImpartedStudy.objects.all()

class StudyDetailView(generics.RetrieveAPIView):
    """Get details of a specific study"""
    queryset = ImpartedStudy.objects.all()
    serializer_class = StudySerializer

    def get_object(self):
        return ImpartedStudy.objects.get(id=self.kwargs['pk'])

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points in kilometers using geopy."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    
    origin = (lat1, lon1)
    destination = (lat2, lon2)
    
    try:
        distance = geodesic(origin, destination).kilometers
        return distance
    except Exception as e:
        logging.error(f"Error calculating distance: {e}")
        return None

@lru_cache(maxsize=100)
def geocode_address(address, country="Spain"):
    """Convert address to latitude and longitude using geopy."""
    try:
        geolocator = Nominatim(user_agent="schools_finder")
        if country and not address.lower().endswith(country.lower()):
            address = f"{address}, {country}"
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        logging.error(f"Error geocoding address: {e}")
        return None, None

class NearestSchoolView(APIView):
    def get(self, request):
        """Find schools based on user filters and calculate distances."""
        address = request.GET.get('address')
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        provinces = request.GET.getlist('provinces')
        school_types = request.GET.getlist('school_types')
        
        if not address or not latitude or not longitude:
            return Response({'error': 'Address and coordinates are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert coordinates to float
            user_lat = float(latitude)
            user_lon = float(longitude)
            
            # Start with all schools
            schools = School.objects.all()
            
            # Apply province filters if provided
            if provinces:
                schools = schools.filter(province__in=provinces)
            
            # Apply school type filters if provided
            if school_types:
                # Separate ownership filters and education level filters
                ownership_types = [t for t in school_types if t in ['public', 'private', 'concertado']]
                education_levels = [t for t in school_types if t in ['infantil', 'primaria', 'secundaria', 'bachillerato', 'fp']]
                
                # Apply ownership type filters
                if ownership_types:
                    ownership_conditions = Q()
                    if 'public' in ownership_types:
                        ownership_conditions |= Q(nature__icontains='Público')
                    if 'private' in ownership_types:
                        ownership_conditions |= Q(nature__icontains='Privado')
                    if 'concertado' in ownership_types:
                        ownership_conditions |= Q(is_concerted=True)
                    
                    schools = schools.filter(ownership_conditions)
                
                # Apply education level filters
                if education_levels:
                    education_conditions = Q()
                    
                    if 'infantil' in education_levels:
                        education_conditions |= Q(studies__name__icontains='infantil')
                    if 'primaria' in education_levels:
                        education_conditions |= Q(studies__name__icontains='primaria')
                    if 'secundaria' in education_levels:
                        education_conditions |= (
                            Q(generic_name__icontains='secundaria') |
                            Q(generic_name__icontains='ESO') |
                            Q(generic_name__icontains='Educación Secundaria')
                        )
                    if 'bachillerato' in education_levels:
                        education_conditions |= (
                            Q(studies__name__icontains='bachillerato') |
                            Q(generic_name__icontains='bachillerato') |
                            Q(center_type__icontains='bachillerato')
                        )
                    if 'fp' in education_levels:
                        education_conditions |= (
                            Q(studies__name__icontains='formación profesional') | 
                            Q(studies__name__icontains='FP') |
                            Q(studies__degree__icontains='formación profesional') |
                            Q(studies__degree__icontains='FP') |
                            Q(studies__degree__icontains='grado') |
                            Q(generic_name__icontains='formación profesional') |
                            Q(generic_name__icontains='FP') |
                            Q(center_type__icontains='formación profesional') |
                            Q(center_type__icontains='FP') |
                            Q(center_type__icontains='ciclo')
                        )
                    
                    if education_conditions:
                        schools = schools.filter(education_conditions).distinct()
            
            # Get schools with valid coordinates and calculate distances
            matching_schools = []
            for school in schools:
                if school.latitude is None or school.longitude is None:
                    continue
                
                # Calculate distance
                distance = calculate_distance(user_lat, user_lon, school.latitude, school.longitude)
                
                if distance is not None:
                    matching_schools.append({
                        'school': school,
                        'distance': distance
                    })
            
            # Sort by distance and take top 10
            matching_schools.sort(key=lambda x: x['distance'])
            matching_schools = matching_schools[:10]
            
            if not matching_schools:
                return Response({
                    'error': 'No schools with location data found matching your criteria'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate travel times only for the top 10 closest schools
            gmaps = googlemaps.Client(key=api_key)
            for entry in matching_schools:
                school = entry['school']
                try:
                    hoy = datetime.now()
                    lunes = hoy + timedelta(days=(7-hoy.weekday()) % 7)  # Próximo lunes
                    llegada_lunes = lunes.replace(hour=8, minute=30, second=0, microsecond=0)
                    llegada_lunes_timestamp = int(llegada_lunes.timestamp())
                    # Walking
                    walking_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="walking",
                        arrival_time=llegada_lunes_timestamp
                    )
                    walking_time = walking_result[0]['legs'][0]['duration']['text'] if walking_result else None
                    
                    # Driving
                    driving_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="driving",
                        arrival_time=llegada_lunes_timestamp
                    )
                    driving_time = driving_result[0]['legs'][0]['duration']['text'] if driving_result else None
                    
                    # Bicycling
                    biking_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="bicycling",
                        arrival_time=llegada_lunes_timestamp
                    )
                    biking_time = biking_result[0]['legs'][0]['duration']['text'] if biking_result else None
                    
                    # Transit
                    transit_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="transit",
                        arrival_time=llegada_lunes_timestamp
                    )
                    transit_time = transit_result[0]['legs'][0]['duration']['text'] if transit_result else None
                    
                    entry['travel_times'] = {
                        'walking': walking_time,
                        'driving': driving_time,
                        'bicycling': biking_time,
                        'transit': transit_time
                    }
                except Exception as e:
                    logger.error(f"Error calculating travel times: {str(e)}")
                    entry['travel_times'] = {
                        'walking': None,
                        'driving': None,
                        'bicycling': None,
                        'transit': None
                    }
            
            # Build response
            school_data = []
            for entry in matching_schools:
                school_dict = SchoolSerializer(entry['school']).data
                school_dict['distance'] = entry['distance']
                school_dict['travel_times'] = entry['travel_times']
                school_data.append(school_dict)
            
            return Response({
                'schools': school_data,
                'total_count': len(matching_schools),
                'search_criteria': {
                    'address': address,
                    'user_location': {'latitude': user_lat, 'longitude': user_lon},
                    'provinces': provinces,
                    'school_types': school_types
                }
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def find_nearest(request):
    """Render the find nearest school page."""
    return render(request, 'schools/find_nearest.html')
