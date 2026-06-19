from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from .models import UserProfile

@receiver(post_save, sender=SocialAccount)
def create_user_profile_from_social_login(sender, instance, created, **kwargs):
    if created:
        user = instance.user
        if not hasattr(user, 'profile'):
            # Check if user is superuser
            if user.is_superuser:
                role = 'admin'
                is_approved = True
            else:
                role = 'student'
                is_approved = False  # Students need admin approval
            UserProfile.objects.create(
                user=user,
                role=role,
                is_active=True,
                is_approved=is_approved
            )

@receiver(post_save, sender=User)
def create_user_profile_for_superuser(sender, instance, created, **kwargs):
    """When superuser is created via createsuperuser, set role to admin"""
    if created and instance.is_superuser:
        if not hasattr(instance, 'profile'):
            UserProfile.objects.create(
                user=instance,
                role='admin',
                is_active=True,
                is_approved=True
            )