"""
API URL configuration for schools app.
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # API endpoints
    path('schools/', views.SchoolListView.as_view(), name='school_list'),
    path('schools/<int:pk>/', views.SchoolDetailView.as_view(), name='school_detail'),
    path('schools/search/', views.SchoolSearchView.as_view(), name='school_search'),
    path('nearest/', views.NearestSchoolView.as_view(), name='nearest_school'),
    path('edit-suggestions/', views.SchoolEditSuggestionView.as_view(), name='edit_suggestion'),
    path('sugerir-centro/', views.suggest_school, name='suggest_school'),
] 