from django.contrib import admin
from django.contrib.sessions.models import Session
from .models import UserSubscription

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'expire_date')
    readonly_fields = ('session_key', 'session_data', 'expire_date')
    ordering = ('-expire_date',)

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_type', 'is_active', 'max_schools_per_search', 'unlimited_api_calls', 'created_at', 'updated_at')
    list_filter = ('subscription_type', 'is_active', 'unlimited_api_calls')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at') 