from django.urls import path
from . import views

urlpatterns = [
    # Page routes
    path('', views.index, name='index'),
    path('find-nearest/', views.find_nearest, name='find_nearest'),
    path('suggest-school/', views.suggest_school, name='suggest_school'),
    path('schools/<int:pk>/', views.school_detail, name='school_detail'),
    path('schools/<int:pk>/edit/', views.edit_school, name='edit_school'),
    
    # API routes
    path('api/schools/', views.SchoolListView.as_view(), name='school_list'),
    path('api/schools/<int:pk>/', views.SchoolDetailView.as_view(), name='school_detail'),
    path('api/schools/search/', views.SchoolSearchView.as_view(), name='school_search'),
    path('api/nearest/', views.NearestSchoolView.as_view(), name='nearest_school'),
    path('api/studies/', views.StudyListView.as_view(), name='study_list'),
    path('api/studies/<int:pk>/', views.StudyDetailView.as_view(), name='study_detail'),
    path('api/suggestions/', views.SchoolSuggestionView.as_view(), name='create_suggestion'),
    path('api/suggestions/list/', views.SchoolSuggestionListView.as_view(), name='list_suggestions'),
    path('api/suggestions/<int:pk>/', views.SchoolSuggestionListView.as_view(), name='update_suggestion'),
    path('api/edit-suggestions/', views.SchoolEditSuggestionView.as_view(), name='create_edit_suggestion'),
    path('api/edit-suggestions/list/', views.SchoolEditSuggestionListView.as_view(), name='list_edit_suggestions'),
    path('api/edit-suggestions/<int:pk>/', views.SchoolEditSuggestionDetailView.as_view(), name='update_edit_suggestion'),
] 