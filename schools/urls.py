from django.urls import path
from . import views

urlpatterns = [
    # Front page
    path('', views.index, name='index'),
    path('schools/<str:pk>/', views.school_detail, name='school-detail-page'),
    path('find-nearest/', views.find_nearest, name='find-nearest'),
    
    # API endpoints
    path('api/schools/', views.SchoolListView.as_view(), name='school-list'),
    path('api/schools/search/', views.SchoolSearchView.as_view(), name='school-search'),
    path('api/schools/nearest/', views.NearestSchoolView.as_view(), name='nearest-school'),
    path('api/schools/<str:pk>/', views.SchoolDetailView.as_view(), name='school-detail'),
    path('api/studies/', views.StudyListView.as_view(), name='study-list'),
    path('api/studies/<int:pk>/', views.StudyDetailView.as_view(), name='study-detail'),
] 