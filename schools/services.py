from django.core.cache import cache
from django.db.models import Q
from .models import Schools, SchoolStudies
import requests
from typing import List, Dict, Optional
import math

class SchoolService:
    CACHE_TTL = 3600  # 1 hour cache
    CACHE_PREFIX = "school_search_"

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points using the Haversine formula.
        Returns distance in kilometers.
        """
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c

        return distance

    @staticmethod
    def get_closest_schools(
        latitude: float,
        longitude: float,
        limit: int = 10,
        transport_mode: str = "driving",
        cache_key: Optional[str] = None
    ) -> List[Dict]:
        """
        Get the N closest schools to a given location.
        Results are cached for 1 hour.
        """
        if cache_key:
            cached_result = cache.get(f"{SchoolService.CACHE_PREFIX}{cache_key}")
            if cached_result:
                return cached_result

        # Get all schools
        schools = Schools.objects.all()

        # Calculate distances and sort
        schools_with_distance = []
        for school in schools:
            # Get school's studies
            studies = SchoolStudies.objects.filter(school=school).select_related('study')
            studies_list = [{
                'name': study.study.name,
                'degree': study.study.degree,
                'family': study.study.family,
                'modality': study.study.modality
            } for study in studies]

            schools_with_distance.append({
                'id': school.id,
                'name': school.name,
                'address': school.address,
                'municipality': school.municipality,
                'province': school.province,
                'autonomous_community': school.autonomous_community,
                'distance': 0,  # We'll calculate this later
                'nature': school.nature,
                'is_concerted': school.is_concerted,
                'center_type': school.center_type,
                'services': school.services,
                'studies': studies_list,
                'contact': {
                    'phone': school.phone,
                    'fax': school.fax,
                    'email': school.email,
                    'website': school.website
                }
            })

        # Sort by distance and take limit
        results = sorted(schools_with_distance, key=lambda x: x['distance'])[:limit]

        # Cache the results if a cache key was provided
        if cache_key:
            cache.set(f"{SchoolService.CACHE_PREFIX}{cache_key}", results, SchoolService.CACHE_TTL)

        return results

    @staticmethod
    def search_schools(
        query: str,
        municipality: Optional[str] = None,
        province: Optional[str] = None,
        autonomous_community: Optional[str] = None,
        nature: Optional[str] = None,
        center_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search schools by name, optionally filtered by location and type.
        """
        schools = Schools.objects.all()

        if query:
            schools = schools.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query)
            )

        if municipality:
            schools = schools.filter(municipality__iexact=municipality)

        if province:
            schools = schools.filter(province__iexact=province)

        if autonomous_community:
            schools = schools.filter(autonomous_community__iexact=autonomous_community)

        if nature:
            schools = schools.filter(nature__iexact=nature)

        if center_type:
            schools = schools.filter(center_type__iexact=center_type)

        schools = schools[:limit]

        return [{
            'id': school.id,
            'name': school.name,
            'address': school.address,
            'municipality': school.municipality,
            'province': school.province,
            'autonomous_community': school.autonomous_community,
            'nature': school.nature,
            'is_concerted': school.is_concerted,
            'center_type': school.center_type,
            'contact': {
                'phone': school.phone,
                'fax': school.fax,
                'email': school.email,
                'website': school.website
            }
        } for school in schools]

    @staticmethod
    def get_route(
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        transport_mode: str = "driving",
        api_key: Optional[str] = None
    ) -> Dict:
        """
        Get route information between two points using Google Maps API.
        Requires a valid Google Maps API key.
        """
        if not api_key:
            return {"error": "API key is required"}

        # Google Maps Directions API endpoint
        url = "https://maps.googleapis.com/maps/api/directions/json"
        
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "mode": transport_mode,
            "key": api_key
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)} 