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
from django.contrib.auth.views import PasswordResetView
from schools.models import SearchHistory
import logging
from django.conf import settings

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
            return render(request, 'users/signup.html', {'form_data': form_data})
            
        # Validate passwords match
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'users/signup.html', {'form_data': form_data})
            
        # Validate password strength
        try:
            validate_password(password1)
        except ValidationError as e:
            for error in e:
                messages.error(request, error)
            return render(request, 'users/signup.html', {'form_data': form_data})
            
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con este correo electrónico.')
            return render(request, 'users/signup.html', {'form_data': form_data})
        
        try:
            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password1
            )
            
            # Log the user in
            login(request, user)
            messages.success(request, '¡Bienvenido a Destino Docente! Tu cuenta ha sido creada con éxito.')
            return redirect('users:dashboard')
            
        except IntegrityError:
            messages.error(request, 'Ya existe un usuario con este correo electrónico.')
            return render(request, 'users/signup.html', {'form_data': form_data})
    
    return render(request, 'users/signup.html')


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
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
        
        if user is not None:
            try:
                # Clear any existing session data
                request.session.flush()
                
                # Log the user in
                login(request, user)
                
                # Set session expiry based on remember me
                if not remember:
                    # If remember me is not checked, session expires in 24 hours
                    request.session.set_expiry(86400)  # 24 hours in seconds
                else:
                    # If remember me is checked, use the default SESSION_COOKIE_AGE (2 weeks)
                    request.session.set_expiry(None)
                
                # Force session save
                request.session.save()
                
                # Verify session was created successfully
                if not request.session.session_key:
                    raise Exception("Failed to create session")
                
                # Log session info for debugging
                logger.info(f"User {user.email} logged in. Session key: {request.session.session_key}")
                logger.info(f"Session expiry: {request.session.get_expiry_date()}")
                
                # Create response with session cookie
                response = redirect('users:dashboard')
                
                # Set additional security headers
                response['X-Frame-Options'] = 'DENY'
                response['X-Content-Type-Options'] = 'nosniff'
                response['X-XSS-Protection'] = '1; mode=block'
                
                # Set session cookie attributes
                session_cookie = response.cookies.get(settings.SESSION_COOKIE_NAME)
                if session_cookie:
                    session_cookie['samesite'] = 'Lax'
                    session_cookie['secure'] = True
                    session_cookie['httponly'] = True
                
                messages.success(request, '¡Conectado con éxito!')
                return response
                
            except Exception as e:
                logger.error(f"Session error during login for user {email}: {str(e)}")
                # Clear any partial session data
                request.session.flush()
                messages.error(request, 'Error al iniciar sesión. Por favor, inténtelo de nuevo.')
                return render(request, 'users/signin.html')
        else:
            messages.error(request, 'Correo electrónico o contraseña incorrectos.')
    
    return render(request, 'users/signin.html')


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
        # Verify session is valid
        if not request.session.session_key:
            logger.warning("Invalid session detected in dashboard view")
            return redirect('users:signin')
            
        # Get user's search history
        search_history = SearchHistory.objects.filter(user=request.user).order_by('-timestamp')[:10]
        
        context = {
            'user': request.user,
            'email': request.user.email,
            'date_joined': request.user.date_joined,
            'last_login': request.user.last_login,
            'search_history': search_history
        }
        return render(request, 'users/dashboard.html', context)
    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}")
        messages.error(request, 'Error al cargar el panel de control. Por favor, inténtelo de nuevo.')
        return redirect('users:signin')


class CustomPasswordResetView(PasswordResetView):
    """
    Custom password reset view that pre-fills the email field.
    """
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'

    def get_initial(self):
        initial = super().get_initial()
        initial['email'] = self.request.GET.get('email', '')
        return initial 

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
            
    return render(request, 'users/settings.html')

@login_required
def profile(request):
    """
    Display user profile information.
    """
    return render(request, 'users/profile.html') 