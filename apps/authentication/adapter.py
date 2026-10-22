# # apps/authentication/adapter.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages
from apps.authentication.models import UserProfile  # Correct import

import logging
logger = logging.getLogger(__name__)

class CustomAccountAdapter(DefaultAccountAdapter):
    def pre_login(self, request, user, **kwargs):
        profile = getattr(user, 'profile', None)
        if not user.is_active or (profile and (not profile.is_active or profile.deleted_at)):
            messages.error(request, 'Your account has been deactivated. Please contact administrator.')
            return redirect('login')
        if profile is None:
            messages.error(request, 'User profile not found. Please contact admin.')
            return redirect('login')
        if not profile.can_login():
            messages.warning(request, 'Your account is pending admin approval.')
            return redirect('login')
        return super().pre_login(request, user, **kwargs)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom adapter for Google OAuth login"""

    def pre_social_login(self, request, sociallogin):
        """
        Link Google login to an existing admin-created user by email.

        Admin-created users do not have a SocialAccount row yet, so without this
        allauth treats the Google identity as a new social signup.
        """
        if sociallogin.is_existing:
            return

        email = self._get_social_email(sociallogin)
        if not email:
            messages.error(request, 'Email not found from Google account.')
            return

        existing_user = User.objects.filter(email__iexact=email).first()
        if not existing_user:
            return

        sociallogin.connect(request, existing_user)
        logger.info("Linked Google account for existing user %s", existing_user.email)

    def _get_social_email(self, sociallogin):
        for email_address in sociallogin.email_addresses:
            if email_address.email:
                return email_address.email.strip().lower()

        email = sociallogin.account.extra_data.get('email')
        if email:
            return email.strip().lower()

        return ''
    
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        if not user.username:
            user.username = user.email.split('@')[0]
            user.save()
        
        # Create UserProfile with pending approval
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'student',
                'is_approved': False,
                'is_active': True,
                'phone_number': ''
            }
        )
        if created:
            logger.info(f"Created pending profile for {user.email}")
        
        return user
    
    def get_login_redirect_url(self, request):
        if not request.user.is_authenticated:
            return reverse('login')
        
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'Profile not found. Contact admin.')
            return reverse('login')
        
        profile = request.user.profile
        
        if not profile.is_approved:
            messages.warning(request, 'Your account is pending admin approval.')
            return reverse('login')
        
        # Role-based redirect
        role_redirects = {
            'admin': 'admin_dashboard',
            'faculty_mentor': 'mentor_dashboard',
            'evaluator': 'evaluator_dashboard',
            'hod': 'hod_dashboard',
            'student': 'student_dashboard',
        }
        return reverse(role_redirects.get(profile.role, 'student_dashboard'))
