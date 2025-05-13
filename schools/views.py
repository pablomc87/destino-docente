from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import Q, F, FloatField, ExpressionWrapper
from datetime import datetime, timedelta
from django.conf import settings
from .models import School, ImpartedStudy, SchoolSuggestion, SchoolEditSuggestion, SearchHistory, APICall
from users.models import UserSubscription
from .serializers import SchoolSerializer, StudySerializer, SchoolSuggestionSerializer, SchoolEditSuggestionSerializer
from rest_framework.views import APIView
from rest_framework import status
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from functools import lru_cache
import logging
import googlemaps
from django.http import JsonResponse
from django.db.models import Count, Avg, Sum
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.permissions import IsAdminUser
from django.http import Http404
from django.utils import timezone
import time
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)
api_key = settings.GOOGLE_MAPS_API_KEY

# Create your views here.

def index(request):
    """Landing page view."""
    return render(request, 'schools/index.html')

def school_detail(request, pk):
    """Render the school detail page"""
    try:
        school = School.objects.get(pk=pk)
        context = {
            'school': school,
            'school_id': school.id,
            'debug': settings.DEBUG
        }
        return render(request, 'schools/school_detail.html', context)
    except School.DoesNotExist:
        raise Http404("School not found")
    except Exception as e:
        if settings.DEBUG:
            raise
        return render(request, 'schools/error.html', {'error': str(e)})

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
            return Response({'error': 'Se requieren dirección y coordenadas'},
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
                    'error': 'No se encontraron centros con datos de ubicación que coincidan con tus criterios'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate travel times only for the top 10 closest schools
            gmaps = googlemaps.Client(key=api_key)
            
            # Track total API calls for this session
            total_api_calls = 0
            start_time = time.time()
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
                    total_api_calls += 1
                    
                    # Driving
                    driving_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="driving",
                        arrival_time=llegada_lunes_timestamp
                    )
                    driving_time = driving_result[0]['legs'][0]['duration']['text'] if driving_result else None
                    total_api_calls += 1
                    
                    # Bicycling
                    biking_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="bicycling",
                        arrival_time=llegada_lunes_timestamp
                    )
                    biking_time = biking_result[0]['legs'][0]['duration']['text'] if biking_result else None
                    total_api_calls += 1
                    
                    # Transit
                    transit_result = gmaps.directions(
                        origin=(user_lat, user_lon),
                        destination=(school.latitude, school.longitude),
                        mode="transit",
                        arrival_time=llegada_lunes_timestamp
                    )
                    transit_time = transit_result[0]['legs'][0]['duration']['text'] if transit_result else None
                    total_api_calls += 1
                    
                    entry['travel_times'] = {
                        'walking': walking_time,
                        'driving': driving_time,
                        'bicycling': biking_time,
                        'transit': transit_time
                    }
                except Exception as e:
                    error_message = str(e)
                    # Check if it's a Google API quota error
                    if hasattr(e, 'response'):
                        try:
                            error_data = e.response.json()
                            if 'error' in error_data:
                                error_message = f"Error de API de Google: {error_data['error'].get('message', 'Error desconocido')}"
                                if 'quota' in error_message.lower():
                                    error_message += f" (Cuota restante: {getattr(e, 'quota_remaining', 'desconocida')})"
                        except:
                            pass
                    
                    logger.error(f"Error calculating travel times: {error_message}")
                    entry['travel_times'] = {
                        'walking': None,
                        'driving': None,
                        'bicycling': None,
                        'transit': None
                    }
                    # Add error information to the response
                    entry['travel_times_error'] = error_message
            
            # Track all API calls for this session in a single record
            if total_api_calls > 0:
                APICall.objects.create(
                    endpoint='directions',
                    api_type='directions',
                    method='GET',
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=get_client_ip(request),
                    response_status=200,
                    response_time=(time.time() - start_time) * 1000,  # Convert to milliseconds
                    quota_remaining=None,
                    total_calls=total_api_calls,
                    place_selected=True  # Since we're calculating travel times, a place was definitely selected
                )
            
            # Build response
            school_data = []
            for entry in matching_schools:
                school_dict = SchoolSerializer(entry['school']).data
                school_dict['distance'] = entry['distance']
                school_dict['travel_times'] = entry['travel_times']
                school_data.append(school_dict)
            
            # Store search history for authenticated users
            if request.user.is_authenticated:
                # Get autonomous community from the first matching school
                autonomous_community = None
                if matching_schools:
                    autonomous_community = matching_schools[0]['school'].autonomous_community

                SearchHistory.objects.create(
                    user=request.user,
                    location=address,
                    latitude=user_lat,
                    longitude=user_lon,
                    results_count=len(matching_schools),
                    provinces=provinces,
                    autonomous_community=autonomous_community,
                    school_types=school_types,
                    results=school_data  # Store the complete search results
                )
            
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

class SchoolSuggestionListView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """List all school suggestions (admin only)."""
        suggestions = SchoolSuggestion.objects.all().order_by('-created_at')
        serializer = SchoolSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update a suggestion's status (admin only)."""
        try:
            suggestion = SchoolSuggestion.objects.get(pk=pk)
        except SchoolSuggestion.DoesNotExist:
            return Response({'error': 'Sugerencia no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        
        # Only allow updating status and notes
        if 'status' in request.data:
            suggestion.status = request.data['status']
        if 'notes' in request.data:
            suggestion.notes = request.data['notes']
        
        suggestion.save()
        serializer = SchoolSuggestionSerializer(suggestion)
        return Response(serializer.data)

def suggest_school(request):
    """Render the school suggestion form page."""
    # Get unique values for dropdowns
    communities = School.objects.exclude(autonomous_community__isnull=True).exclude(autonomous_community='').values_list('autonomous_community', flat=True).distinct().order_by('autonomous_community')
    provinces = School.objects.exclude(province__isnull=True).exclude(province='').values_list('province', 'autonomous_community').distinct().order_by('province')
    municipalities = School.objects.exclude(municipality__isnull=True).exclude(municipality='').values_list('municipality', flat=True).distinct().order_by('municipality')
    center_types = School.objects.exclude(center_type__isnull=True).exclude(center_type='').values_list('center_type', flat=True).distinct().order_by('center_type')
    studies = ImpartedStudy.objects.values('name').distinct().order_by('name')
    
    context = {
        'communities': communities,
        'provinces': provinces,
        'municipalities': municipalities,
        'center_types': center_types,
        'studies': studies,
    }
    return render(request, 'schools/suggest_school.html', context)

def edit_school(request, pk):
    """Render the edit school page"""
    try:
        school = School.objects.get(pk=pk)
        # Use the serializer to get all fields
        serializer = SchoolSerializer(school)
        context = {
            'school': serializer.data,  # Use the serialized data
            'debug': settings.DEBUG
        }
        return render(request, 'schools/edit_school.html', context)
    except School.DoesNotExist:
        raise Http404("School not found")
    except Exception as e:
        if settings.DEBUG:
            raise
        return render(request, 'schools/error.html', {'error': str(e)})

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

class SchoolEditSuggestionListView(generics.ListAPIView):
    """API endpoint for listing school edit suggestions"""
    queryset = SchoolEditSuggestion.objects.all()
    serializer_class = SchoolEditSuggestionSerializer
    permission_classes = [IsAdminUser]

class SchoolEditSuggestionDetailView(generics.RetrieveUpdateAPIView):
    """API endpoint for updating school edit suggestions"""
    queryset = SchoolEditSuggestion.objects.all()
    serializer_class = SchoolEditSuggestionSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status == 'approved':
            # Update the school with the suggested changes
            school = instance.school
            school.name = instance.name
            school.address = instance.address
            school.postal_code = instance.postal_code
            school.municipality = instance.municipality
            school.province = instance.province
            school.community = instance.community
            school.nature = instance.nature
            school.center_type = instance.center_type
            school.generic_name = instance.generic_name
            school.is_concerted = instance.is_concerted
            school.latitude = instance.latitude
            school.longitude = instance.longitude
            school.save()

@api_view(['POST'])
@login_required
def toggle_search_favorite(request, pk):
    """Toggle favorite status of a search history entry."""
    try:
        search = SearchHistory.objects.get(pk=pk, user=request.user)
        search.is_favorite = not search.is_favorite
        search.save()
        return JsonResponse({
            'status': 'success',
            'is_favorite': search.is_favorite
        })
    except SearchHistory.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Búsqueda no encontrada'
        }, status=404)

@api_view(['POST'])
@login_required
def delete_search(request, pk):
    """Delete a search history entry."""
    try:
        search = SearchHistory.objects.get(pk=pk, user=request.user)
        search.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Búsqueda eliminada correctamente'
        })
    except SearchHistory.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Búsqueda no encontrada'
        }, status=404)

@staff_member_required
def api_stats(request):
    """
    Display API call statistics.
    """
    # Get time range from query params
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)
    
    # Get API calls within time range
    api_calls = APICall.objects.filter(timestamp__gte=start_date)
    
    # Get statistics by API type
    type_stats = api_calls.values('api_type').annotate(
        total_calls=Sum('total_calls'),
        avg_response_time=ExpressionWrapper(Sum('response_time') / F('total_calls'), output_field=FloatField()),
        success_rate=Count('id', filter=Q(response_status__lt=400)) * 100.0 / Count('id')
    ).order_by('-total_calls')
    
    # Get statistics by endpoint
    endpoint_stats = api_calls.values('endpoint').annotate(
        total_calls=Sum('total_calls'),
        avg_response_time=ExpressionWrapper(Sum('response_time') / F('total_calls'), output_field=FloatField()),
        success_rate=Count('id', filter=Q(response_status__lt=400)) * 100.0 / Count('id')
    ).order_by('-total_calls')
    
    # Get statistics by user
    user_stats = api_calls.filter(user__isnull=False).values(
        'user__email'
    ).annotate(
        total_calls=Sum('total_calls'),
        avg_response_time=ExpressionWrapper(Sum('response_time') / F('total_calls'), output_field=FloatField())
    ).order_by('-total_calls')
    
    # Get statistics by method
    method_stats = api_calls.values('method').annotate(
        total_calls=Sum('total_calls'),
        avg_response_time=ExpressionWrapper(Sum('response_time') / F('total_calls'), output_field=FloatField())
    ).order_by('-total_calls')
    
    context = {
        'type_stats': type_stats,
        'endpoint_stats': endpoint_stats,
        'user_stats': user_stats,
        'method_stats': method_stats,
        'total_calls': api_calls.count(),
        'avg_response_time': api_calls.aggregate(Avg('response_time'))['response_time__avg'],
        'days': days,
    }
    
    return render(request, 'schools/api_stats.html', context)

@api_view(['POST'])
def track_google_api(request):
    """Track Google API calls made from the frontend."""
    try:
        data = request.data
        
        # Create API call record
        APICall.objects.create(
            endpoint=data.get('endpoint'),
            api_type=data.get('api_type'),
            method=data.get('method', 'GET'),
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            response_status=200,
            response_time=data.get('response_time', 0),  # Get response time from frontend
            quota_remaining=None,
            total_calls=data.get('total_calls'),
            place_selected=data.get('place_selected')
        )
        
        return Response({'status': 'success'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@api_view(['GET'])
def check_api_limits(request):
    """Check if API usage is within limits."""
    try:
        # Check if user is authenticated and has a paid subscription
        is_paid_user = False
        max_schools = 10  # Default for free users
        
        if request.user.is_authenticated:
            try:
                subscription = request.user.subscription
                is_paid_user = subscription.is_paid
                max_schools = subscription.max_schools_per_search
            except UserSubscription.DoesNotExist:
                # Create a free subscription for the user
                UserSubscription.objects.create(user=request.user)
        
        # If user has unlimited API calls, return immediately
        if is_paid_user and request.user.subscription.unlimited_api_calls:
            return Response({
                'within_limits': True,
                'is_paid_user': True,
                'max_schools': max_schools,
                'unlimited_api_calls': True
            })

        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Get daily and monthly usage
        daily_usage = APICall.objects.filter(
            timestamp__date=today
        ).aggregate(
            total_calls=Sum('total_calls')
        )['total_calls'] or 0
        
        monthly_usage = APICall.objects.filter(
            timestamp__date__gte=month_start
        ).aggregate(
            total_calls=Sum('total_calls')
        )['total_calls'] or 0
        
        # Check against limits
        daily_limit = 300
        monthly_limit = 10000
        
        return Response({
            'within_limits': daily_usage < daily_limit and monthly_usage < monthly_limit,
            'daily_usage': daily_usage,
            'monthly_usage': monthly_usage,
            'daily_limit': daily_limit,
            'monthly_limit': monthly_limit,
            'is_paid_user': is_paid_user,
            'max_schools': max_schools,
            'unlimited_api_calls': is_paid_user and request.user.subscription.unlimited_api_calls
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def search(request):
    """Search view for schools with filters."""
    # Get search parameters
    search_query = request.GET.get('search', '')
    autonomous_community = request.GET.get('autonomous_community', '')
    province = request.GET.get('province', '')
    municipality = request.GET.get('municipality', '')
    center_type = request.GET.get('center_type', '')
    nature = request.GET.get('nature', '')
    distance = request.GET.get('distance', '')
    sort_by = request.GET.get('sort', 'relevance')
    page = request.GET.get('page', 1)

    # Start with all schools
    schools = School.objects.all()

    # Apply filters
    if search_query:
        schools = schools.filter(
            Q(name__icontains=search_query) |
            Q(municipality__icontains=search_query) |
            Q(province__icontains=search_query)
        )

    if autonomous_community:
        schools = schools.filter(autonomous_community=autonomous_community)

    if province:
        schools = schools.filter(province=province)

    if municipality:
        schools = schools.filter(municipality=municipality)

    if center_type:
        schools = schools.filter(center_type=center_type)

    if nature:
        schools = schools.filter(nature=nature)

    # Apply sorting
    if sort_by == 'name':
        schools = schools.order_by('name')
    elif sort_by == 'distance':
        schools = schools.order_by('distance')
    else:  # relevance
        schools = schools.order_by('-id')  # Default sorting by newest first

    # Get unique values for filters
    autonomous_communities = School.objects.values_list('autonomous_community', flat=True).distinct().order_by('autonomous_community')
    provinces = School.objects.values_list('province', flat=True).distinct().order_by('province')
    municipalities = School.objects.values_list('municipality', flat=True).distinct().order_by('municipality')
    center_types = School.objects.values_list('center_type', flat=True).distinct().order_by('center_type')

    # Pagination
    paginator = Paginator(schools, 10)  # Show 10 schools per page
    schools = paginator.get_page(page)

    context = {
        'schools': schools,
        'total_results': schools.paginator.count,
        'autonomous_communities': autonomous_communities,
        'provinces': provinces,
        'municipalities': municipalities,
        'center_types': center_types,
        'search_query': search_query,
        'autonomous_community': autonomous_community,
        'province': province,
        'municipality': municipality,
        'center_type': center_type,
        'nature': nature,
        'distance': distance,
        'sort_by': sort_by,
    }

    return render(request, 'schools/search.html', context)

@api_view(['GET'])
def school_list(request):
    """API endpoint to list schools with optional filtering."""
    try:
        # Get query parameters
        name = request.GET.get('name', '')
        autonomous_community = request.GET.get('autonomous_community', '')
        province = request.GET.get('province', '')
        municipality = request.GET.get('municipality', '')
        center_type = request.GET.get('center_type', '')
        nature = request.GET.get('nature', '')

        # Start with all schools
        schools = School.objects.all()

        # Apply filters
        if name:
            schools = schools.filter(name__icontains=name)
        if autonomous_community:
            schools = schools.filter(autonomous_community=autonomous_community)
        if province:
            schools = schools.filter(province=province)
        if municipality:
            schools = schools.filter(municipality=municipality)
        if center_type:
            schools = schools.filter(center_type=center_type)
        if nature:
            schools = schools.filter(nature=nature)

        # Serialize the results
        serializer = SchoolSerializer(schools, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def province_list(request):
    """API endpoint to list provinces, optionally filtered by autonomous community."""
    try:
        community = request.GET.get('community', '')
        provinces = School.objects.values_list('province', flat=True).distinct()
        
        if community:
            provinces = provinces.filter(autonomous_community=community)
        
        return Response(list(provinces))
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def municipality_list(request):
    """API endpoint to list municipalities, optionally filtered by province."""
    try:
        province = request.GET.get('province', '')
        municipalities = School.objects.values_list('municipality', flat=True).distinct()
        
        if province:
            municipalities = municipalities.filter(province=province)
        
        return Response(list(municipalities))
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
