import time
from django.utils.deprecation import MiddlewareMixin
from .models import APICall

class GoogleAPITrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track Google API calls made by the application.
    """
    def process_request(self, request):
        # Store the start time
        request._api_start_time = time.time()
        
    def process_response(self, request, response):
        # Only track Google API calls
        if not hasattr(request, '_google_api_call'):
            return response
            
        # Calculate response time
        response_time = (time.time() - request._api_start_time) * 1000  # Convert to milliseconds
        
        # Create API call record
        APICall.objects.create(
            endpoint=request._google_api_endpoint,
            api_type=request._google_api_type,
            method=request.method,
            user=request.user if request.user.is_authenticated else None,
            ip_address=self.get_client_ip(request),
            response_status=response.status_code,
            response_time=response_time,
            quota_remaining=getattr(response, '_quota_remaining', None)
        )
        
        return response
        
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
        
    def determine_api_type(self, path):
        """
        Determine the type of API being called based on the endpoint path.
        """
        path = path.lower()
        
        if '/centros/' in path:
            return 'schools'
        elif '/estudios/' in path:
            return 'studies'
        elif '/buscar-cercanos/' in path:
            return 'search'
        elif '/directions/' in path or '/travel-times/' in path:
            return 'directions'
        elif '/sugerir-centro/' in path or '/sugerencias/' in path:
            return 'suggestions'
        elif '/historial-busquedas/' in path:
            return 'history'
        else:
            return 'other'  # Default type for unknown endpoints 