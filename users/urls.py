"""
URL configuration for users app.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('registrarse/', views.signup, name='signup'),
    path('conectarse/', views.signin, name='signin'),
    path('salir/', views.signout, name='signout'),
    path('perfil/', views.profile, name='profile'),
    path('panel/', views.dashboard, name='dashboard'),
    path('ajustes/', views.settings, name='settings'),
    path('check-session/', views.check_session, name='check_session'),
    
    # Password Reset URLs
    path('restablecer-contraseña/', 
         views.CustomPasswordResetView.as_view(),
         name='password_reset'),
    path('restablecer-contraseña/hecho/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('restablecer-contraseña/confirmar/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('restablecer-contraseña/completado/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ),
         name='password_reset_complete'),
] 