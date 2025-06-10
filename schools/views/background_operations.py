from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from ..models import APICall, School
from users.models import UserSubscription
from django.db.models import Sum
from ..utils.client import get_client_ip

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


@api_view(['GET'])
def get_province_list(request):
    """API endpoint to list provinces, optionally filtered by autonomous community."""
    try:
        community = request.GET.get('comunidad_autonoma', '')  # Changed from 'community'
        provinces = School.objects.values_list('province', flat=True).distinct()
        
        if community:
            provinces = provinces.filter(autonomous_community=community)
        
        return Response(list(provinces.order_by('province')))
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_municipality_list(request):
    """API endpoint to list municipalities, optionally filtered by province."""
    try:
        province = request.GET.get('provincia', '')
        municipalities = School.objects.values_list('municipality', flat=True).distinct()
        
        if province:
            municipalities = municipalities.filter(province=province)
        
        return Response(list(municipalities))
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
