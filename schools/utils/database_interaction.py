import time
from django.db.models import Q
from schools.models import APICall
from schools.utils.client import get_client_ip
from schools.utils.distances import calculate_distance
from schools.models import School
import logging


def filter_schools(queryset, autonomous_communities=None, ownership_types=None, education_levels=None, advanced_school_types=None):
    """
    Filter schools by autonomous community, ownership types, education levels, and advanced school types.
    All filter groups use AND logic - schools must meet ALL selected criteria.
    
    Args:
        queryset: Base queryset of schools to filter
        autonomous_communities (list): List of autonomous communities to filter by
        ownership_types (list): List of ownership types to filter by (public, private, concertado)
        education_levels (list): List of education levels to filter by (infantil, primaria, secundaria, bachillerato, fp,
            idiomas, musica_artes_escenicas, artes_plasticas_diseno)
        advanced_school_types (list): List of specific center types to filter by
    
    Returns:
        QuerySet: Filtered queryset of schools
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Starting filter_schools with {len(queryset)} schools")
    
    # Clean and validate filters
    autonomous_communities = [ac for ac in (autonomous_communities or []) if ac and ac.strip()]
    ownership_types = [ot for ot in (ownership_types or []) if ot and ot.strip()]
    education_levels = [el for el in (education_levels or []) if el and el.strip()]
    advanced_school_types = [ast for ast in (advanced_school_types or []) if ast and ast.strip()]
    
    logger.debug(f"Cleaned autonomous communities filter: {autonomous_communities}")
    logger.debug(f"Cleaned ownership types filter: {ownership_types}")
    logger.debug(f"Cleaned education levels filter: {education_levels}")
    logger.debug(f"Cleaned advanced school types filter: {advanced_school_types}")
    
    initial_count = queryset.count()
    
    # Apply filters with AND logic between groups
    if autonomous_communities:
        logger.debug(f"Filtering by autonomous communities: {autonomous_communities}")
        queryset = queryset.filter(autonomous_community__in=autonomous_communities)
        logger.debug(f"After autonomous communities filter: {queryset.count()} schools")

    if ownership_types:
        logger.debug(f"Filtering by ownership types: {ownership_types}")
        ownership_conditions = Q()
        if 'public' in ownership_types:
            ownership_conditions |= Q(nature__icontains='Público')
        if 'private' in ownership_types:
            # Private schools must be private in nature AND not concertado
            ownership_conditions |= (Q(nature__icontains='Privado') & Q(is_concerted=False))
        if 'concertado' in ownership_types:
            # Concertado schools must be private in nature AND concertado
            ownership_conditions |= (Q(nature__icontains='Privado') & Q(is_concerted=True))
        queryset = queryset.filter(ownership_conditions)
        logger.debug(f"After ownership filter: {queryset.count()} schools")

    if education_levels:
        logger.debug(f"Filtering by education levels: {education_levels}")
        education_conditions = Q()
        
        # Handle basic education levels only
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
        if 'idiomas' in education_levels:
            education_conditions |= (
                Q(studies__name__icontains='idioma') |
                Q(studies__name__icontains='lengua extranjera') |
                Q(studies__name__icontains='lenguas extranjeras') |
                Q(studies__degree__icontains='idioma') |
                Q(generic_name__icontains='idioma') |
                Q(center_type__icontains='idioma')
            )
        if 'musica_artes_escenicas' in education_levels:
            education_conditions |= (
                Q(studies__name__icontains='música') |
                Q(studies__name__icontains='musica') |
                Q(studies__name__icontains='escénica') |
                Q(studies__name__icontains='escenica') |
                Q(studies__degree__icontains='música') |
                Q(studies__degree__icontains='danza') |
                Q(generic_name__icontains='música') |
                Q(generic_name__icontains='artes escénicas') |
                Q(center_type__icontains='conservatorio') |
                Q(center_type__icontains='danza')
            )
        if 'artes_plasticas_diseno' in education_levels:
            education_conditions |= (
                Q(studies__name__icontains='artes plásticas') |
                Q(studies__name__icontains='artes plasticas') |
                Q(studies__name__icontains='diseño') |
                Q(studies__name__icontains='diseno') |
                Q(studies__degree__icontains='plástica') |
                Q(studies__degree__icontains='diseño') |
                Q(generic_name__icontains='artes plásticas') |
                Q(generic_name__icontains='diseño') |
                Q(center_type__icontains='diseño') |
                Q(center_type__icontains='plástica')
            )
        
        queryset = queryset.filter(education_conditions).distinct()
        logger.debug(f"After education level filter: {queryset.count()} schools")

    if advanced_school_types:
        logger.debug(f"Filtering by advanced school types: {advanced_school_types}")
        advanced_conditions = Q()
        
        # Advanced school types are specific center types
        for advanced_type in advanced_school_types:
            advanced_conditions |= Q(center_type__icontains=advanced_type)
        
        queryset = queryset.filter(advanced_conditions).distinct()
        logger.debug(f"After advanced school types filter: {queryset.count()} schools")
    
    final_count = queryset.count()
    logger.debug(f"Filtering complete. Initial count: {initial_count}, Final count: {final_count}")
    return queryset

def find_nearest_schools(user_lat, user_lon, autonomous_communities=None, ownership_types=None, education_levels=None, advanced_school_types=None, limit=3):
    """
    Find the nearest schools to a given location, optionally filtered by autonomous communities, ownership types, education levels, and advanced school types.
    
    Args:
        user_lat (float): User's latitude
        user_lon (float): User's longitude
        autonomous_communities (list, optional): List of autonomous communities to filter by
        ownership_types (list, optional): List of ownership types to filter by (public, private, concertado)
        education_levels (list, optional): List of education levels to filter by (infantil, primaria, secundaria, bachillerato, fp)
        advanced_school_types (list, optional): List of specific center types to filter by
        limit (int, optional): Maximum number of schools to return. Defaults to 3.
    
    Returns:
        list: List of dictionaries containing school objects and their distances in kilometers
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Starting find_nearest_schools with coordinates: ({user_lat}, {user_lon})")
    logger.debug(f"Filters - Autonomous communities: {autonomous_communities}, Ownership types: {ownership_types}, Education levels: {education_levels}, Advanced school types: {advanced_school_types}")
    logger.debug(f"Limit: {limit}")
    
    try:
        # Start with filtered schools that have valid coordinates
        base_query = School.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        logger.debug(f"Base query count (with valid coordinates): {base_query.count()}")
        
        schools = filter_schools(base_query, autonomous_communities, ownership_types, education_levels, advanced_school_types)
        logger.debug(f"After filtering: {schools.count()} schools")

        # Calculate distances and sort in memory
        matching = []
        for school in schools:
            distance = calculate_distance(user_lat, user_lon, school.latitude, school.longitude)
            if distance is not None:
                matching.append({
                    'school': school,
                    'distance': distance
                })
        
        logger.debug(f"Schools with valid distances: {len(matching)}")
        
        # Sort by distance and take top N
        matching.sort(key=lambda x: x['distance'])
        result = matching[:limit]
        
        logger.debug(f"Final result count: {len(result)}")
        if result:
            logger.debug(f"Closest school distance: {result[0]['distance']:.2f}km")
            logger.debug(f"Furthest school distance: {result[-1]['distance']:.2f}km")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in find_nearest_schools: {str(e)}")
        logger.exception("Full traceback:")
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