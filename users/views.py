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
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'users/signup.html', {'form_data': form_data})
            
        # Validate passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
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
            messages.error(request, 'A user with this email already exists.')
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
            messages.success(request, 'Account created successfully! Welcome to School Finder.')
            return redirect('index')
            
        except IntegrityError:
            messages.error(request, 'An error occurred while creating your account. Please try again.')
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
            login(request, user)
            
            # Set session expiry based on remember me
            if not remember:
                request.session.set_expiry(0)  # Session expires when browser closes
                
            messages.success(request, 'Successfully signed in!')
            return redirect('users:dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'users/signin.html')


@login_required
def signout(request):
    """
    Handle user sign out.
    """
    logout(request)
    messages.success(request, 'Successfully signed out!')
    return redirect('index')


@login_required
def dashboard(request):
    """
    Display user dashboard.
    """
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
                messages.error(request, 'Please enter a valid email address.')
                return redirect('users:settings')
                
            # Check if email is already taken
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                messages.error(request, 'This email is already in use.')
                return redirect('users:settings')
                
            # Update email
            request.user.email = new_email
            request.user.username = new_email  # Update username to match email
            request.user.save()
            messages.success(request, 'Email updated successfully.')
            
        elif action == 'update_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Verify current password
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('users:settings')
                
            # Validate new password
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
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
            messages.success(request, 'Password updated successfully.')
            
        elif action == 'delete_account':
            password = request.POST.get('password')
            
            # Verify password
            if not request.user.check_password(password):
                messages.error(request, 'Password is incorrect.')
                return redirect('users:settings')
                
            # Delete user
            request.user.delete()
            messages.success(request, 'Your account has been deleted.')
            return redirect('index')
            
    return render(request, 'users/settings.html')

@login_required
def profile(request):
    """
    Display user profile information.
    """
    return render(request, 'users/profile.html') 