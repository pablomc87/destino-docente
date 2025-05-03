"""
URL configuration for schools app.
"""
from django.urls import path
from . import views

app_name = 'schools'

urlpatterns = [
    # Page routes
    path('', views.index, name='index'),
    path('schools/', views.SchoolListView.as_view(), name='school_list'),
    path('schools/<int:pk>/', views.school_detail, name='school_detail'),
    path('schools/<int:pk>/edit/', views.edit_school, name='edit_school'),
    path('find-nearest/', views.find_nearest, name='find_nearest'),
    path('suggest-school/', views.suggest_school_page, name='suggest_school_page'),
] 