from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
from schools.models import School, SearchHistory
from schools.utils.distances import get_travel_times
from schools.utils.database_interaction import log_api_call, find_nearest_schools
from schools.serializers import SchoolSerializer, SchoolSuggestionSerializer, SchoolEditSuggestionSerializer
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)
api_key = settings.GOOGLE_MAPS_API_KEY

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

class FreeSchoolTravelSearch(APIView):
    """Free tier search that returns top 3 nearest schools with travel times."""
    
    def get(self, request):
        """Find top 3 nearest schools based on user filters and calculate travel times."""
        address = request.GET.get('address')
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        provinces = request.GET.getlist('provinces')
        school_types = request.GET.getlist('school_types')
        
        if not address or not latitude or not longitude:
            return Response({'error': 'Se requieren dirección y coordenadas'},
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert coordinates to float
            user_lat = float(latitude)
            user_lon = float(longitude)
            
            # Find nearest schools using the utility function
            top_schools = find_nearest_schools(user_lat, user_lon, provinces, school_types, limit=3)
            
            if not top_schools:
                return Response({
                    'error': 'No se encontraron centros con datos de ubicación que coincidan con tus criterios'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate travel times
            for entry in top_schools:
                entry['travel_times'] = get_travel_times(
                    user_lat, user_lon, 
                    entry['school'].latitude, entry['school'].longitude
                )

            # Log API call
            log_api_call(request, endpoint='directions', total_calls=len(top_schools) * 4)
            
            # Build response
            school_data = []
            for entry in top_schools:
                school_dict = SchoolSerializer(entry['school']).data
                school_dict['distance'] = entry['distance']
                school_dict['travel_times'] = entry['travel_times']
                school_data.append(school_dict)
            
            # Store search history
            if request.user.is_authenticated:
                SearchHistory.objects.create(
                    user=request.user,
                    location=address,
                    latitude=user_lat,
                    longitude=user_lon,
                    results_count=len(top_schools),
                    provinces=provinces,
                    school_types=school_types,
                    results=school_data,
                    includes_travel_times=True
                )
            
            return Response({
                'schools': school_data,
                'total_count': len(top_schools),
                'search_criteria': {
                    'address': address,
                    'user_location': {'latitude': user_lat, 'longitude': user_lon},
                    'provinces': provinces,
                    'school_types': school_types
                }
            })
            
        except ValueError as e:
            logger.error(f"Invalid coordinates in FreeSchoolTravelSearch: {e}")
            return Response(
                {'error': 'Las coordenadas proporcionadas no son válidas'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in FreeSchoolTravelSearch: {e}")
            return Response(
                {'error': 'Ha ocurrido un error al procesar la búsqueda'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SchoolSuggestionView(APIView):
    def post(self, request):
        """Create a new school suggestion."""
        print("Received data:", request.data)  # Debug print
        print("Data types:", {k: type(v) for k, v in request.data.items()})  # Debug data types
        serializer = SchoolSuggestionSerializer(data=request.data)
        if serializer.is_valid():
            print("Validated data:", serializer.validated_data)  # Debug validated data
            instance = serializer.save()
            print("Created instance:", instance.__dict__)  # Debug created instance
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Validation errors:", serializer.errors)  # Debug validation errors
        print("Error details:", {k: str(v) for k, v in serializer.errors.items()})  # Debug error details
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SchoolEditSuggestionView(APIView):
    """API endpoint for creating school edit suggestions"""
    permission_classes = []  # Remove authentication requirement

    def post(self, request):
        """Create a new school edit suggestion."""
        print("=== SchoolEditSuggestionView.post called ===")  # Debug print
        print("Request method:", request.method)  # Debug print
        print("Received data:", request.data)  # Debug print
        print("Data types:", {k: type(v) for k, v in request.data.items()})  # Debug data types
        
        serializer = SchoolEditSuggestionSerializer(data=request.data)
        if serializer.is_valid():
            print("Validated data:", serializer.validated_data)  # Debug validated data
            instance = serializer.save()
            print("Created instance:", instance.__dict__)  # Debug created instance
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Validation errors:", serializer.errors)  # Debug validation errors
        print("Error details:", {k: str(v) for k, v in serializer.errors.items()})  # Debug error details
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileSchoolSearch(APIView):
    """
    Search for schools within the user profile.
    Returns nearest schools with optional travel times calculation.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Find nearest schools based on user filters and calculate travel times if requested."""
        address = request.GET.get('address')
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        provinces = request.GET.getlist('provinces')
        school_types = request.GET.getlist('school_types')
        include_travel_times = request.GET.get('include_travel_times', 'false').lower() == 'true'
        school_ids = request.GET.getlist('school_ids')  # Get selected school IDs
        search_history_id = request.GET.get('search_history_id')  # Get search history ID if provided
        limit = int(request.GET.get('limit', 10))  # Default to 10 schools
        
        if not address or not latitude or not longitude:
            return Response(
                {'error': 'Se requieren dirección y coordenadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Convert coordinates to float
            user_lat = float(latitude)
            user_lon = float(longitude)
            
            # If we're just calculating travel times for an existing search
            if include_travel_times and search_history_id:
                try:
                    # Get the existing search history entry
                    search_history = SearchHistory.objects.get(id=search_history_id, user=request.user)
                    
                    # Get the schools from the search history
                    school_data = search_history.results
                    
                    # Calculate travel times only for selected schools
                    for school in school_data:
                        if str(school['id']) in school_ids:
                            school['travel_times'] = get_travel_times(
                                user_lat, user_lon,
                                school['latitude'], school['longitude']
                            )
                    
                    # Update the search history with travel times
                    search_history.results = school_data
                    search_history.includes_travel_times = True
                    search_history.save()
                    
                    # Log API call for travel times
                    log_api_call(
                        request,
                        endpoint='directions',
                        total_calls=len(school_ids) * 4
                    )
                    
                    return Response({
                        'schools': school_data,
                        'total_count': len(school_data),
                        'search_criteria': {
                            'address': address,
                            'user_location': {'latitude': user_lat, 'longitude': user_lon},
                            'provinces': provinces,
                            'school_types': school_types,
                            'include_travel_times': True
                        },
                        'search_history_id': search_history.id
                    })
                    
                except SearchHistory.DoesNotExist:
                    logger.error(f"Search history entry {search_history_id} not found")
                    return Response(
                        {'error': 'No se encontró el historial de búsqueda'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # If this is a new search or we're not calculating travel times
            # Find nearest schools using the utility function
            top_schools = find_nearest_schools(
                user_lat, user_lon,
                provinces, school_types,
                limit=limit
            )
            
            if not top_schools:
                return Response({
                    'error': 'No se encontraron centros con datos de ubicación que coincidan con tus criterios'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Build response
            school_data = []
            for entry in top_schools:
                school_dict = SchoolSerializer(entry['school']).data
                school_dict['distance'] = entry['distance']
                school_data.append(school_dict)
            
            try:
                # Create new search history entry
                search_history = SearchHistory.objects.create(
                    user=request.user,
                    location=address,
                    latitude=user_lat,
                    longitude=user_lon,
                    results_count=len(top_schools),
                    provinces=provinces,
                    school_types=school_types,
                    results=school_data,
                    includes_travel_times=False
                )
                
                # Include search history ID in response
                response_data = {
                    'schools': school_data,
                    'total_count': len(top_schools),
                    'search_criteria': {
                        'address': address,
                        'user_location': {'latitude': user_lat, 'longitude': user_lon},
                        'provinces': provinces,
                        'school_types': school_types,
                        'include_travel_times': False
                    },
                    'search_history_id': search_history.id
                }
                
                return Response(response_data)
                
            except Exception as e:
                logger.error(f"Error handling search history: {str(e)}")
                # Continue with the response even if search history fails
                return Response({
                    'schools': school_data,
                    'total_count': len(top_schools),
                    'search_criteria': {
                        'address': address,
                        'user_location': {'latitude': user_lat, 'longitude': user_lon},
                        'provinces': provinces,
                        'school_types': school_types,
                        'include_travel_times': False
                    }
                })
            
        except ValueError as e:
            logger.error(f"Invalid coordinates in ProfileSchoolSearch: {e}")
            return Response(
                {'error': 'Las coordenadas proporcionadas no son válidas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in ProfileSchoolSearch: {str(e)}")
            logger.error(f"Request data: {request.GET}")
            return Response(
                {'error': 'Ha ocurrido un error al procesar la búsqueda'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
