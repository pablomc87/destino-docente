from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q
from .models import School, ImpartedStudy
from .serializers import SchoolSerializer, StudySerializer

# Create your views here.

def index(request):
    """Render the main search page"""
    return render(request, 'schools/index.html')

def school_detail(request, pk):
    """Render the school detail page"""
    return render(request, 'schools/school_detail.html')

class SchoolListView(generics.ListAPIView):
    """List all schools"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def get_queryset(self):
        return School.objects.all()

class SchoolDetailView(generics.RetrieveAPIView):
    """Get details of a specific school"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def get_object(self):
        return School.objects.get(id=self.kwargs['pk'])

class SchoolSearchView(generics.ListAPIView):
    """Search schools by name, municipality, or province"""
    serializer_class = SchoolSerializer

    def get_queryset(self):
        query = self.request.query_params.get('name', '')
        if not query:
            return School.objects.none()
        
        return School.objects.filter(
            Q(name__icontains=query) |
            Q(municipality__icontains=query) |
            Q(province__icontains=query)
        )[:50]  # Limit results to 50 schools

class StudyListView(generics.ListAPIView):
    """List all studies"""
    queryset = ImpartedStudy.objects.all()
    serializer_class = StudySerializer

    def get_queryset(self):
        return ImpartedStudy.objects.all()

class StudyDetailView(generics.RetrieveAPIView):
    """Get details of a specific study"""
    queryset = ImpartedStudy.objects.all()
    serializer_class = StudySerializer

    def get_object(self):
        return ImpartedStudy.objects.get(id=self.kwargs['pk'])
