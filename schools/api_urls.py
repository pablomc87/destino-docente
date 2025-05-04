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
    path('edit-suggestions/', views.SchoolEditSuggestionView.as_view(), name='edit_suggestion'),
    path('suggest-school/', views.suggest_school, name='suggest_school'),
] 