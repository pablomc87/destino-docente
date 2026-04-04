from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from schools.models import School, SearchHistory
from schools.utils.distances import get_travel_times
from schools.utils.database_interaction import log_api_call, find_nearest_schools
from schools.serializers import SchoolSerializer, SchoolSuggestionSerializer, SchoolEditSuggestionSerializer
from schools.throttles import SuggestionRateThrottle
from rest_framework.views import APIView
from rest_framework import status
from users.models import UserSubscription
import logging

logger = logging.getLogger(__name__)

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
        return get_object_or_404(School, pk=self.kwargs['pk'])

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

class SchoolSearch(APIView):
    """Search that returns nearest schools with optional travel times."""
    
    def get(self, request):
        """Find top 3 nearest schools based on user filters and calculate travel times."""
        address = request.GET.get('address')
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        # Handle both array and single value formats
        autonomous_communities = request.GET.getlist('autonomous_communities[]') or request.GET.getlist('autonomous_communities')
        ownership_types = request.GET.getlist('ownership_types[]') or request.GET.getlist('ownership_types')
        education_levels = request.GET.getlist('education_levels[]') or request.GET.getlist('education_levels')
        advanced_school_types = request.GET.getlist('advanced_school_types[]') or request.GET.getlist('advanced_school_types')
        include_travel_times = request.GET.get('include_travel_times', 'false').lower() == 'true'
        all_results = request.GET.get('all_results', 'false').lower() == 'true'
        
        logger.debug(f"Received autonomous_communities: {autonomous_communities}")
        logger.debug(f"Received ownership_types: {ownership_types}")
        logger.debug(f"Received education_levels: {education_levels}")
        logger.debug(f"Received advanced_school_types: {advanced_school_types}")
        logger.debug(f"Include travel times: {include_travel_times}")
        logger.debug(f"All results requested: {all_results}")
        
        if not address or not latitude or not longitude:
            return Response({'error': 'Se requieren dirección y coordenadas'},
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert coordinates to float
            user_lat = float(latitude)
            user_lon = float(longitude)
            
            # Combine education levels with advanced school types
            all_education_filters = education_levels + advanced_school_types
            
            logger.debug(f"Combined education filters: {all_education_filters}")
            
            # Determine the limit based on user subscription and travel times request
            if request.user.is_authenticated:
                # Authenticated users: always get 300 schools, but travel times depend on subscription
                try:
                    subscription = request.user.subscription
                    travel_times_limit = subscription.max_schools_per_search
                    logger.debug(f"Authenticated user subscription limit for travel times: {travel_times_limit}")
                except UserSubscription.DoesNotExist:
                    # Create a free subscription for the user
                    subscription = UserSubscription.objects.create(
                        user=request.user,
                        subscription_type='free',
                        max_schools_per_search=10,
                        unlimited_api_calls=False
                    )
                    travel_times_limit = subscription.max_schools_per_search
                    logger.debug(f"Created free subscription with travel times limit: {travel_times_limit}")
                
                # Always get 300 schools for authenticated users
                limit = 300
                logger.debug(f"Authenticated user getting {limit} schools")
            else:
                # Non-authenticated users: 300 schools without travel times, 3 with travel times
                if include_travel_times:
                    limit = 3
                    logger.debug(f"Non-authenticated user with travel times: limit = {limit}")
                else:
                    limit = 300
                    logger.debug(f"Non-authenticated user without travel times: limit = {limit}")
            
            # Find nearest schools using the utility function with proper filter separation
            top_schools = find_nearest_schools(
                user_lat, user_lon, 
                autonomous_communities=autonomous_communities,
                ownership_types=ownership_types,
                education_levels=education_levels,
                advanced_school_types=advanced_school_types,
                limit=limit
            )
            
            if not top_schools:
                return Response({
                    'error': 'No se encontraron centros con datos de ubicación que coincidan con tus criterios'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate travel times based on user type and request
            if include_travel_times:
                if request.user.is_authenticated:
                    # For authenticated users: calculate travel times only for their subscription limit
                    schools_with_travel_times = min(len(top_schools), travel_times_limit)
                    logger.debug(f"Calculating travel times for first {schools_with_travel_times} schools")
                    
                    for i, entry in enumerate(top_schools):
                        if i < schools_with_travel_times:
                            entry['travel_times'] = get_travel_times(
                                user_lat, user_lon, 
                                entry['school'].latitude, entry['school'].longitude
                            )
                        else:
                            entry['travel_times'] = None
                    
                    # Log API call for travel times
                    log_api_call(request, endpoint='directions', total_calls=schools_with_travel_times * 4)
                else:
                    # For non-authenticated users: calculate travel times for all schools (limited to 3)
                    for entry in top_schools:
                        entry['travel_times'] = get_travel_times(
                            user_lat, user_lon, 
                            entry['school'].latitude, entry['school'].longitude
                        )
                    
                    # Log API call for travel times
                    log_api_call(request, endpoint='directions', total_calls=len(top_schools) * 4)
            
            # Build response
            school_data = []
            for entry in top_schools:
                school_dict = SchoolSerializer(entry['school']).data
                school_dict['distance'] = entry['distance']
                # Only include travel_times if they were calculated and exist
                if include_travel_times and 'travel_times' in entry and entry['travel_times'] is not None:
                    school_dict['travel_times'] = entry['travel_times']
                school_data.append(school_dict)
            
            # Handle pagination
            from django.core.paginator import Paginator
            page = request.GET.get('page', 1)
            schools_per_page = 10
            
            logger.debug(f"Starting pagination: page={page}, total_schools={len(school_data)}, all_results={all_results}")
            
            # If all_results is requested, return all schools without pagination
            if all_results:
                logger.debug("Returning all results without pagination")
                paginated_schools = school_data
                paginator = None
            else:
                # Normal pagination
                try:
                    page = int(page)
                    logger.debug(f"Converted page to int: {page}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting page to int: {e}")
                    page = 1
                
                try:
                    paginator = Paginator(school_data, schools_per_page)
                    logger.debug(f"Created paginator: total_pages={paginator.num_pages}")
                    
                    paginated_schools = paginator.page(page)
                    logger.debug(f"Got paginated schools: count={len(list(paginated_schools))}")
                    
                except Exception as e:
                    logger.error(f"Error in pagination: {e}")
                    # Fallback: return all schools without pagination
                    paginated_schools = school_data
                    paginator = None
            
            # Debug logging
            logger.debug(f"Pagination debug: total_schools={len(school_data)}, page={page}, total_pages={paginator.num_pages if paginator else 'N/A'}, schools_on_page={len(list(paginated_schools))}")
            
            # Store search history
            if request.user.is_authenticated:
                SearchHistory.objects.create(
                    user=request.user,
                    location=address,
                    latitude=user_lat,
                    longitude=user_lon,
                    results_count=len(top_schools),
                    autonomous_community=autonomous_communities[0] if autonomous_communities else '',  # Store first community if any
                    school_types=ownership_types + education_levels + advanced_school_types,  # Include all filter types
                    results=school_data,
                    includes_travel_times=include_travel_times
                )
            
            # Debug the response structure
            response_data = {
                'schools': list(paginated_schools),
                'total_count': len(top_schools),
                'search_criteria': {
                    'address': address,
                    'user_location': {'latitude': user_lat, 'longitude': user_lon},
                    'autonomous_communities': autonomous_communities,
                    'ownership_types': ownership_types,
                    'education_levels': education_levels,
                    'advanced_school_types': advanced_school_types,
                    'include_travel_times': include_travel_times
                }
            }
            
            # Add paginator data only if pagination was successful and not all_results
            if paginator is not None and not all_results:
                response_data['paginator'] = {
                    'current_page': paginated_schools.number,
                    'total_pages': paginator.num_pages,
                    'has_previous': paginated_schools.has_previous(),
                    'has_next': paginated_schools.has_next(),
                    'previous_page_number': paginated_schools.previous_page_number() if paginated_schools.has_previous() else None,
                    'next_page_number': paginated_schools.next_page_number() if paginated_schools.has_next() else None,
                    'page_range': list(paginator.page_range),
                }
                logger.debug(f"Added paginator data: {response_data['paginator']}")
            elif all_results:
                logger.debug("All results returned - no paginator data needed")
            else:
                logger.warning("No paginator data added - pagination failed")
            
            logger.debug(f"API Response structure: {response_data.keys()}")
            
            return Response(response_data)
            
        except ValueError as e:
            logger.error(f"Invalid coordinates in SchoolSearch: {e}")
            return Response(
                {'error': 'Las coordenadas proporcionadas no son válidas'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Error in SchoolSearch: %s", e)
            return Response(
                {'error': 'Ha ocurrido un error al procesar la búsqueda'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SchoolSuggestionView(APIView):
    throttle_classes = [SuggestionRateThrottle]

    def post(self, request):
        """Create a new school suggestion."""
        serializer = SchoolSuggestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SchoolEditSuggestionView(APIView):
    """API endpoint for creating school edit suggestions."""
    throttle_classes = [SuggestionRateThrottle]

    def post(self, request):
        """Create a new school edit suggestion."""
        serializer = SchoolEditSuggestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


