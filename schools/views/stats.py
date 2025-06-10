from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, ExpressionWrapper, F, FloatField, Avg
from django.db.models.query_utils import Q
from django.utils import timezone
from django.utils.timezone import timedelta
from django.shortcuts import render
from ..models import APICall


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