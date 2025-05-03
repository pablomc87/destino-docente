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
    path('edit-suggestions/', views.edit_school_suggestion, name='edit_suggestion'),
    path('suggest-school/', views.suggest_school, name='suggest_school'),
] 