import time
from django.db.models import Q
from schools.models import APICall
from schools.utils.client import get_client_ip
from schools.utils.distances import calculate_distance
from schools.models import School


def filter_schools(queryset, autonomous_communities, school_types):
    """Filter schools by autonomous community and school types (ownership, education level)."""
    if autonomous_communities and any(community for community in autonomous_communities if community):  # Only filter if there are non-empty values
        queryset = queryset.filter(autonomous_community__in=autonomous_communities)

    if school_types and any(school_type for school_type in school_types if school_type):  # Only filter if there are non-empty values
        ownership_types = [t for t in school_types if t in ['public', 'private', 'concertado']]
        education_levels = [t for t in school_types if t in ['infantil', 'primaria', 'secundaria', 'bachillerato', 'fp']]

        # Ownership
        if ownership_types:
            ownership_conditions = Q()
            if 'public' in ownership_types:
                ownership_conditions |= Q(nature__icontains='Público')
            if 'private' in ownership_types:
                ownership_conditions |= Q(nature__icontains='Privado')
            if 'concertado' in ownership_types:
                ownership_conditions |= Q(is_concerted=True)
            queryset = queryset.filter(ownership_conditions)

        # Education level
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
                queryset = queryset.filter(education_conditions).distinct()
    return queryset

def find_nearest_schools(user_lat, user_lon, provinces=None, school_types=None, limit=3):
    """
    Find the nearest schools to a given location, optionally filtered by provinces and school types.
    
    Args:
        user_lat (float): User's latitude
        user_lon (float): User's longitude
        provinces (list, optional): List of provinces to filter by
        school_types (list, optional): List of school types to filter by
        limit (int, optional): Maximum number of schools to return. Defaults to 3.
    
    Returns:
        list: List of dictionaries containing school objects and their distances in kilometers
    """
    try:
        # Start with filtered schools that have valid coordinates
        base_query = School.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        
        schools = filter_schools(base_query, provinces, school_types)

        # Calculate distances and sort in memory
        matching = []
        for school in schools:
            distance = calculate_distance(user_lat, user_lon, school.latitude, school.longitude)
            if distance is not None:
                matching.append({
                    'school': school,
                    'distance': distance
                })
        
        # Sort by distance and take top N
        matching.sort(key=lambda x: x['distance'])
        result = matching[:limit]
        
        return result
        
    except Exception as e:
        print(f"Error in find_nearest_schools: {e}")
        return []

def log_api_call(request, endpoint, total_calls, response_status=200, quota_remaining=None, place_selected=True, start_time=None):
    """Log a Google API call session."""
    APICall.objects.create(
        endpoint=endpoint,
        api_type='directions',
        method='GET',
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request),
        response_status=response_status,
        response_time=(time.time() - start_time) * 1000 if start_time else 0,
        quota_remaining=quota_remaining,
        total_calls=total_calls,
        place_selected=place_selected
    )