from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import Q
import math
import requests
from django.conf import settings
from .models import School, ImpartedStudy
from .serializers import SchoolSerializer, StudySerializer
from rest_framework.views import APIView
from rest_framework import status

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
    """Calculate the distance between two points in kilometers using the Haversine formula."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

class NearestSchoolView(APIView):
    def get(self, request):
        """Find the nearest school to a given postal code within a specified region."""
        postal_code = request.GET.get('postal_code')
        province = request.GET.get('province')
        municipality = request.GET.get('municipality')
        
        if not postal_code:
            return Response({'error': 'Postal code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Start with all schools
            schools = School.objects.all()
            
            # Apply location filters
            if province:
                schools = schools.filter(province__iexact=province)
            if municipality:
                schools = schools.filter(municipality__iexact=municipality)
            
            # Find schools in the same postal code
            schools = schools.filter(postal_code=postal_code)
            
            if not schools.exists():
                # If no schools found in the same postal code, try nearby postal codes
                schools = School.objects.all()
                if province:
                    schools = schools.filter(province__iexact=province)
                if municipality:
                    schools = schools.filter(municipality__iexact=municipality)
                
                # Get the first school in the area
                nearest_school = schools.first()
                if not nearest_school:
                    return Response({'error': 'No schools found in the specified location'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # If multiple schools in the same postal code, return the first one
                nearest_school = schools.first()
            
            return Response({
                'school': SchoolSerializer(nearest_school).data,
                'location_info': {
                    'postal_code': postal_code,
                    'province': province,
                    'municipality': municipality
                }
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def find_nearest(request):
    """Render the find nearest school page."""
    return render(request, 'schools/find_nearest.html')
