"""
Views for the users app.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from schools.models import SearchHistory
import logging
from django.conf import settings as django_settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from datetime import timedelta
from .models import UserSubscription


logger = logging.getLogger(__name__)

def signup(request):
    """
    Handle user registration.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        form_data = {
            'email': email, 
            'password1': password1,
            'password2': password2
        }
        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Por favor, introduce un correo electrónico válido.')
            return render(request, 'signup.html', {'form_data': form_data})
            
        # Validate passwords match
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'signup.html', {'form_data': form_data})
            
        # Validate password strength
        try:
            validate_password(password1)
        except ValidationError as e:
            for error in e:
                messages.error(request, error)
            return render(request, 'signup.html', {'form_data': form_data})
            
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con este correo electrónico.')
            return render(request, 'signup.html', {'form_data': form_data})
        
        try:
            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password1
            )
            
            # Create free subscription for the user
            subscription = UserSubscription.objects.create(
                user=user,
                subscription_type='free',
                max_schools_per_search=10,
                unlimited_api_calls=False
            )
            
            # Generate verification token and send email
            token = subscription.generate_email_verification_token()
            verification_url = f"{django_settings.SITE_URL}/usuarios/verificar-correo/{token}/"
            
            # Render email template
            html_message = render_to_string('verify_email.html', {
                'verification_url': verification_url
            })
            plain_message = strip_tags(html_message)
            
            # Send verification email
            send_mail(
                'Verifica tu correo electrónico - Destino Docente',
                plain_message,
                django_settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=html_message,
                fail_silently=False,
            )
            
            messages.success(request, '¡Bienvenido a Destino Docente! Tu cuenta ha sido creada con éxito. Por favor, verifica tu correo electrónico para activar tu cuenta.')
            return redirect('users:dashboard')
            
        except IntegrityError:
            messages.error(request, 'Ya existe un usuario con este correo electrónico.')
            return render(request, 'signup.html', {'form_data': form_data})
    
    return render(request, 'signup.html')


def signin(request):
    """
    Handle user sign in.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        # Try to find user by email
        try:
            user_obj = User.objects.get(email=email)
            subscription = UserSubscription.objects.get(user=user_obj)
            
            # Check if email is verified before attempting authentication
            if not subscription.is_email_verified:
                # Generate new verification token and send email
                token = subscription.generate_email_verification_token()
                verification_url = f"{django_settings.SITE_URL}/usuarios/verificar-correo/{token}/"
                
                # Render email template
                html_message = render_to_string('verify_email.html', {
                    'verification_url': verification_url
                })
                plain_message = strip_tags(html_message)
                
                # Send verification email
                send_mail(
                    'Verifica tu correo electrónico - Destino Docente',
                    plain_message,
                    django_settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                messages.error(request, 'Por favor, verifica tu correo electrónico antes de iniciar sesión. Se ha enviado un nuevo correo de verificación.')
                return render(request, 'signin.html')
            
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
        except UserSubscription.DoesNotExist:
            messages.error(request, 'Error en la cuenta. Por favor, contacta con soporte.')
            return render(request, 'signin.html')
        
        if user is not None:
            try:
                # Clear any existing session data
                request.session.flush()
                
                # Create new session
                request.session.create()
                
                # Login and set session data
                login(request, user)
                
                # Set session expiry based on remember me
                if not remember:
                    request.session.set_expiry(86400)  # 24 hours
                else:
                    request.session.set_expiry(None)  # Use default (2 weeks)
                
                # Force session save
                request.session.save()
                
                logger.debug("Session created successfully after login")
                messages.success(request, '¡Conectado con éxito!')
                return redirect('users:dashboard')
            except Exception as e:
                logger.error(f"Error during login: {str(e)}", exc_info=True)
                messages.error(request, 'Error al iniciar sesión. Por favor, inténtelo de nuevo.')
                return render(request, 'signin.html')
        else:
            messages.error(request, 'Correo electrónico o contraseña incorrectos.')
    
    return render(request, 'signin.html')


@login_required
def signout(request):
    """
    Handle user sign out.
    """
    logout(request)
    messages.success(request, '¡Desconectado con éxito!')
    return redirect('index')


@login_required(login_url='/usuarios/conectarse/')
def dashboard(request):
    """
    Display user dashboard.
    """
    try:
        # Get user's search history with pagination
        search_history_queryset = SearchHistory.objects.filter(user=request.user).order_by('-timestamp')
        
        # Pagination
        from django.core.paginator import Paginator
        page = request.GET.get('page', 1)
        paginator = Paginator(search_history_queryset, 10)  # Show 20 searches per page
        
        try:
            search_history = paginator.page(page)
        except (ValueError, TypeError):
            search_history = paginator.page(1)
        
        # Get the selected search if search_id is provided
        selected_search = None
        search_id = request.GET.get('search_id')
        if search_id:
            try:
                selected_search = SearchHistory.objects.get(id=search_id, user=request.user)
            except SearchHistory.DoesNotExist:
                messages.warning(request, 'La búsqueda seleccionada no existe.')
        
        context = {
            'user': request.user,
            'email': request.user.email,
            'date_joined': request.user.date_joined,
            'last_login': request.user.last_login,
            'search_history': search_history,
            'selected_search': selected_search
        }
        return render(request, 'dashboard.html', context)
    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}")
        messages.error(request, 'Error al cargar el panel de control. Por favor, inténtelo de nuevo.')
        return redirect('users:signin')


class CustomPasswordResetView(PasswordResetView):
    """
    Custom password reset view that pre-fills the email field.
    """
    template_name = 'password_reset.html'
    email_template_name = 'password_reset_email.html'
    subject_template_name = 'password_reset_subject.txt'
    success_url = '/usuarios/restablecer-contraseña/hecho/'

    def get_initial(self):
        initial = super().get_initial()
        initial['email'] = self.request.GET.get('email', '')
        return initial

    def form_valid(self, form):
        self.reset_url_token = 'users:password_reset_confirm'
        self.reset_url_name = 'users:password_reset_complete'
        self.success_url = reverse('users:password_reset_done')
        try:
            return super().form_valid(form)
        except Exception as e:
            logger.exception("Error sending password reset email: %s", e)
            messages.error(
                self.request,
                'Error al enviar el correo electrónico. Por favor, inténtelo de nuevo.',
            )
            return self.form_invalid(form)

@login_required
def settings(request):
    """
    Handle user settings updates.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_email':
            new_email = request.POST.get('email')
            
            # Validate email
            try:
                validate_email(new_email)
            except ValidationError:
                messages.error(request, 'Por favor, introduce un correo electrónico válido.')
                return redirect('users:settings')
                
            # Check if email is already taken
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                messages.error(request, 'Este correo electrónico ya está en uso.')
                return redirect('users:settings')
                
            # Update email
            request.user.email = new_email
            request.user.username = new_email  # Update username to match email
            request.user.save()
            messages.success(request, 'Correo electrónico actualizado con éxito.')
            
        elif action == 'update_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Verify current password
            if not request.user.check_password(current_password):
                messages.error(request, 'La contraseña actual es incorrecta.')
                return redirect('users:settings')
                
            # Validate new password
            if new_password != confirm_password:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('users:settings')
                
            try:
                validate_password(new_password)
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
                return redirect('users:settings')
                
            # Update password
            request.user.set_password(new_password)
            request.user.save()
            
            # Re-authenticate user
            login(request, request.user)
            messages.success(request, 'Contraseña actualizada con éxito.')
            
        elif action == 'delete_account':
            password = request.POST.get('password')
            
            # Verify password
            if not request.user.check_password(password):
                messages.error(request, 'La contraseña es incorrecta.')
                return redirect('users:settings')
                
            # Delete user
            request.user.delete()
            messages.success(request, 'Tu cuenta ha sido eliminada.')
            return redirect('index')
            
    return render(request, 'settings.html')

@login_required
def profile(request):
    """
    Display user profile information.
    """
    # Get user's search history
    search_history = SearchHistory.objects.filter(user=request.user).order_by('-timestamp')[:3]
    
    context = {
        'user': request.user,
        'search_history': search_history
    }
    return render(request, 'profile.html', context)

@login_required
def check_session(request):
    """
    Check if the user's session is valid.
    Returns 200 if valid, 401 if not.
    """
    try:
        if request.user.is_authenticated and request.session.session_key:
            request.session.save()
            return HttpResponse(status=200)

        logger.warning(
            "Session validation failed (authenticated=%s, has_key=%s)",
            request.user.is_authenticated,
            bool(request.session.session_key),
        )
        return HttpResponse(status=401)
    except Exception as e:
        logger.exception("Error checking session: %s", e)
        return HttpResponse(status=503)

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Custom password reset confirm view.
    """
    template_name = 'password_reset_confirm.html'
    success_url = '/usuarios/restablecer-contraseña/completado/'

    def get_success_url(self):
        return reverse('users:password_reset_complete')

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        return super().form_valid(form)
    
def verify_email(request, token):
    try:
        subscription = UserSubscription.objects.get(email_verification_token=token)
        
        # Check if token is expired (24 hours)
        if subscription.email_verification_sent_at < timezone.now() - timedelta(hours=24):
            messages.error(request, 'El enlace de verificación ha expirado. Por favor, solicita uno nuevo.')
            return redirect('users:signin')
        
        # Mark user as verified
        subscription.is_email_verified = True
        subscription.save()
        
        # Clear verification token
        subscription.email_verification_token = None
        subscription.save()
        
        messages.success(request, '¡Correo electrónico verificado! Ya puedes iniciar sesión.')
        return redirect('users:signin')
        
    except UserSubscription.DoesNotExist:
        messages.error(request, 'Enlace de verificación inválido.')
        return redirect('users:signin')
