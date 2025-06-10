from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from schools import views

urlpatterns = [
    # Admin URLs
    path('admin/', admin.site.urls),
    
    # Page routes
    path('', views.render_templates.index, name='index'),
    path('', include('schools.urls', namespace='schools')),
    path('usuarios/', include('users.urls', namespace='users')),
    
    # API routes
    path('api/', include('schools.api_urls', namespace='api')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Configure error handlers
handler500 = 'schools.views.handler500'
