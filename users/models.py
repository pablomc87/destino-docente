"""
Models for the users app.
"""

from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone

class UserSubscription(models.Model):
    """Model to track user subscription status and preferences."""
    SUBSCRIPTION_TYPES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    subscription_type = models.CharField(max_length=10, choices=SUBSCRIPTION_TYPES, default='free')
    is_active = models.BooleanField(default=True)
    max_schools_per_search = models.IntegerField(default=10)  # Number of schools to return per search
    unlimited_api_calls = models.BooleanField(default=False)  # Whether user has unlimited API calls
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
    
    def __str__(self):
        return f"{self.user.email} - {self.subscription_type}"
    
    @property
    def is_paid(self):
        """Check if user has a paid subscription."""
        return self.subscription_type in ['basic', 'premium'] and self.is_active

    def generate_email_verification_token(self):
        """Generate a new email verification token."""
        token = uuid.uuid4()
        self.email_verification_token = token
        self.email_verification_sent_at = timezone.now()
        self.save()
        return token