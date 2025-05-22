"""
URL configuration for schools app.
"""
from django.urls import path
from . import views

app_name = 'schools'

urlpatterns = [
    # Page routes
    path('', views.index, name='index'),
    path('centros/', views.SchoolListView.as_view(), name='school_list'),
    path('centros/<str:pk>/', views.school_detail, name='school_detail'),
    path('centros/<str:pk>/editar/', views.edit_school, name='edit_school'),
    path('contacto/', views.contact, name='contact'),
    path('quienes-somos/', views.about, name='about'),
    path('buscar-cercanos/', views.find_nearest, name='find_nearest'),
    path('sugerir-centro/', views.suggest_school, name='suggest_school'),
    path('buscar/', views.search, name='search'),
    
    # Search history actions
    path('api/historial-busquedas/<int:pk>/favorito/', views.toggle_search_favorite, name='toggle_search_favorite'),
    path('api/historial-busquedas/<int:pk>/eliminar/', views.delete_search, name='delete_search'),
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/track-google-api/', views.track_google_api, name='track_google_api'),
    path('api/check-limits/', views.check_api_limits, name='check_api_limits'),
    path('api/provinces/', views.province_list, name='province_list'),
    path('api/municipalities/', views.municipality_list, name='municipality_list'),
] 