from django.urls import path
from . import views

urlpatterns = [
    # Front page
    path('', views.index, name='index'),
    path('schools/<int:pk>/', views.school_detail, name='school-detail-page'),
    
    # API endpoints
    path('api/schools/search/', views.SchoolSearchView.as_view(), name='school-search'),
    path('api/schools/<str:pk>/', views.SchoolDetailView.as_view(), name='school-detail'),
    path('api/schools/', views.SchoolListView.as_view(), name='school-list'),
    path('api/studies/', views.StudyListView.as_view(), name='study-list'),
    path('api/studies/<int:pk>/', views.StudyDetailView.as_view(), name='study-detail'),
] 