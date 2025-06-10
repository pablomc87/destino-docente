import logging
from geopy.distance import geodesic
import logging
from datetime import datetime, timedelta
from django.conf import settings
import googlemaps

logger = logging.getLogger(__name__)

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
    
def get_travel_times(user_lat, user_lon, school_lat, school_lon):
    """Get travel times for walking, driving, bicycling, and transit using Google Maps."""
    api_key = settings.GOOGLE_MAPS_API_KEY
    gmaps = googlemaps.Client(key=api_key)
    hoy = datetime.now()
    lunes = hoy + timedelta(days=(7-hoy.weekday()) % 7)
    llegada_lunes = lunes.replace(hour=8, minute=30, second=0, microsecond=0)
    llegada_lunes_timestamp = int(llegada_lunes.timestamp())

    modes = ['walking', 'driving', 'bicycling', 'transit']
    times = {}
    for mode in modes:
        try:
            result = gmaps.directions(
                origin=(user_lat, user_lon),
                destination=(school_lat, school_lon),
                mode=mode,
                arrival_time=llegada_lunes_timestamp
            )
            times[mode] = result[0]['legs'][0]['duration']['text'] if result else None
        except Exception as e:
            logger.error(f"Error calculating {mode} travel time: {e}")
            times[mode] = None
    return times