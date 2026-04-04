from django.shortcuts import render, redirect
from django.http import Http404
from django.conf import settings
from ..models import School, ImpartedStudy
from ..serializers import SchoolSerializer
from django.db.models.query_utils import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
import logging
import requests

logger = logging.getLogger(__name__)
_GENERIC_HTML_ERROR = "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo más tarde."


def index(request):
    """Landing page view."""
    return render(request, 'schools/index.html')

def school_detail(request, pk):
    """Render the school detail page"""
    try:
        # Store search parameters in session if coming from search
        if request.META.get('HTTP_REFERER', '').startswith(request.build_absolute_uri('/buscar/')):
            request.session['search_params'] = request.META.get('HTTP_REFERER', '').split('?', 1)[1] if '?' in request.META.get('HTTP_REFERER', '') else ''

        school = School.objects.get(pk=pk)
        context = {
            'school': school,
            'school_id': school.id,
        }
        return render(request, 'schools/school_detail.html', context)
    except School.DoesNotExist:
        raise Http404("School not found")
    except Exception as e:
        if settings.DEBUG:
            raise
        logger.exception("school_detail failed: %s", e)
        return render(request, 'schools/error.html', {'error': _GENERIC_HTML_ERROR})
    

def find_nearest(request):
    """Render the find nearest school page."""
    # Get unique values for advanced filters (same as dashboard)
    school_types = School.objects.exclude(
        center_type__isnull=True
    ).exclude(
        center_type=''
    ).values_list(
        'center_type', flat=True
    ).distinct().order_by('center_type')
    
    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'school_types': school_types,
    }
    return render(request, 'schools/find_nearest.html', context)

def suggest_school(request):
    """Render the school suggestion form page."""
    # Get unique values for dropdowns
    communities = School.objects.exclude(autonomous_community__isnull=True).exclude(autonomous_community='').values_list('autonomous_community', flat=True).distinct().order_by('autonomous_community')
    provinces = School.objects.exclude(province__isnull=True).exclude(province='').values_list('province', 'autonomous_community').distinct().order_by('province')
    municipalities = School.objects.exclude(municipality__isnull=True).exclude(municipality='').values_list('municipality', flat=True).distinct().order_by('municipality')
    center_types = School.objects.exclude(center_type__isnull=True).exclude(center_type='').values_list('center_type', flat=True).distinct().order_by('center_type')
    studies = ImpartedStudy.objects.values('name').distinct().order_by('name')
    
    context = {
        'communities': communities,
        'provinces': provinces,
        'municipalities': municipalities,
        'center_types': center_types,
        'studies': studies,
    }
    return render(request, 'schools/suggest_school.html', context)

def edit_school(request, pk):
    """Render the edit school page"""
    try:
        school = School.objects.get(pk=pk)
        # Use the serializer to get all fields
        serializer = SchoolSerializer(school)
        context = {
            'school': serializer.data,  # Use the serialized data
            'debug': settings.DEBUG
        }
        return render(request, 'schools/edit_school.html', context)
    except School.DoesNotExist:
        raise Http404("School not found")
    except Exception as e:
        if settings.DEBUG:
            raise
        logger.exception("edit_school failed: %s", e)
        return render(request, 'schools/error.html', {'error': _GENERIC_HTML_ERROR})
    
def search(request):
    """Search view for schools with filters."""
    # Get search parameters with Spanish names
    search_query = request.GET.get('buscar', '')
    autonomous_community = request.GET.get('comunidad', '')
    province = request.GET.get('provincia', '')
    municipality = request.GET.get('municipio', '')
    center_type = request.GET.get('tipo', '')
    nature = request.GET.get('titularidad', '')
    page = request.GET.get('pagina', 1)

    # Start with all schools
    schools = School.objects.all()

    # Apply filters
    if search_query:
        schools = schools.filter(
            Q(name__icontains=search_query) |
            Q(municipality__icontains=search_query) |
            Q(province__icontains=search_query)
        )

    if autonomous_community:
        schools = schools.filter(autonomous_community=autonomous_community)

    if province:
        schools = schools.filter(province=province)

    if municipality:
        schools = schools.filter(municipality=municipality)

    if center_type:
        schools = schools.filter(center_type=center_type)

    if nature:
        schools = schools.filter(nature=nature)

    # Sort by relevance (newest first)
    schools = schools.order_by('-id')

    # Get unique values for filters
    autonomous_communities = School.objects.values_list('autonomous_community', flat=True).distinct().order_by('autonomous_community')
    provinces = School.objects.values_list('province', flat=True).distinct().order_by('province')
    municipalities = School.objects.values_list('municipality', flat=True).distinct().order_by('municipality')
    center_types = School.objects.values_list('center_type', flat=True).distinct().order_by('center_type')

    # Pagination
    paginator = Paginator(schools, 10)  # Show 10 schools per page
    schools = paginator.get_page(page)

    context = {
        'schools': schools,
        'total_results': schools.paginator.count,
        'autonomous_communities': autonomous_communities,
        'provinces': provinces,
        'municipalities': municipalities,
        'center_types': center_types,
        'search_query': search_query,
        'autonomous_community': autonomous_community,
        'province': province,
        'municipality': municipality,
        'center_type': center_type,
        'nature': nature,
    }

    return render(request, 'schools/search.html', context)

def handler500(request):
    """Handle 500 server errors."""
    return render(request, 'schools/error.html', {
        'error': 'Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo más tarde.'
    }, status=500)

def contact(request):
    """Handle contact form submissions."""
    if request.method == 'POST':
        # Verify hCaptcha
        hcaptcha_response = request.POST.get('h-captcha-response')
        if not hcaptcha_response:
            messages.error(request, 'Por favor, verifica que no eres un robot.')
            return redirect('schools:contact')
            
        # Verify with hCaptcha
        verify_url = 'https://hcaptcha.com/siteverify'
        values = {
            'secret': settings.HCAPTCHA_SECRET_KEY,
            'response': hcaptcha_response
        }
        response = requests.post(verify_url, data=values)
        result = response.json()
        
        if not result.get('success', False):
            messages.error(request, 'Error en la verificación. Por favor, inténtalo de nuevo.')
            return redirect('schools:contact')
        
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Prepare email content
        email_subject = f'Contacto Destino Docente: {subject}'
        email_message = f"""
        Nombre: {name}
        Email: {email}
        
        Mensaje:
        {message}
        """
        
        if not getattr(settings, "CONTACT_EMAIL", "").strip():
            logger.error("CONTACT_EMAIL is not configured; contact form cannot deliver")
            messages.error(
                request,
                "El formulario de contacto no está configurado en el servidor. Por favor, inténtalo más tarde.",
            )
        else:
            try:
                send_mail(
                    subject=email_subject,
                    message=email_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL.strip()],
                    fail_silently=False,
                )
                messages.success(request, '¡Mensaje enviado con éxito! Te responderemos lo antes posible.')
            except Exception as e:
                logger.exception("contact send_mail failed: %s", e)
                messages.error(request, 'Ha ocurrido un error al enviar el mensaje. Por favor, inténtalo de nuevo más tarde.')
        
        return redirect('schools:contact')
    
    context = {
        'hcaptcha_site_key': settings.HCAPTCHA_SITE_KEY
    }
    return render(request, 'schools/contact.html', context)

def about(request):
    """Render the about page."""
    return render(request, 'schools/about.html')

@login_required(login_url='users:signin')
def premium_distance_search(request):
    """Render the find nearest schools page."""
    # Get unique values for advanced filters
    school_types = School.objects.exclude(
        center_type__isnull=True
    ).exclude(
        center_type=''
    ).values_list(
        'center_type', flat=True
    ).distinct().order_by('center_type')
    
    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'debug': settings.DEBUG,
        'school_types': school_types,
    }
    return render(request, 'schools/find_nearest_dashboard.html', context)