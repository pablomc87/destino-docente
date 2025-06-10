from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import SearchHistory

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