# # apps/authentication/adapter.py

# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from django.contrib.auth.models import User
# from django.shortcuts import redirect
# from django.urls import reverse
# from django.contrib import messages
# import logging

# logger = logging.getLogger(__name__)

# class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
#     """
#     Custom adapter to handle Google OAuth login with role-based redirection
#     """
    
#     def pre_social_login(self, request, sociallogin):
#         """
#         Called before social login. We can check if user exists and handle
#         any pre-login logic here.
#         """
#         # Get email from Google
#         email = sociallogin.account.extra_data.get('email')
#         if not email:
#             messages.error(request, 'Email not found from Google account.')
#             return
        
#         # Check if user already exists
#         try:
#             user = User.objects.get(email=email)
#             # User exists, update their profile with Google info if needed
#             sociallogin.user = user
#             logger.info(f"User {email} logged in via Google")
#         except User.DoesNotExist:
#             # User doesn't exist, will be created automatically
#             logger.info(f"New user {email} signing up via Google")
#             pass
        
#         return super().pre_social_login(request, sociallogin)
    
#     def save_user(self, request, sociallogin, form=None):
#         """
#         Save user and handle role-based redirection
#         """
#         user = super().save_user(request, sociallogin, form)
        
#         # Set username to email prefix if not set
#         if not user.username:
#             user.username = user.email.split('@')[0]
#             user.save()
        
#         # Ensure profile exists with 'pending' role
#         profile, created = Profile.objects.get_or_create(user=user)
#         if created:
#             profile.role = 'pending'
#             profile.is_approved = False
#             profile.save()
#             logger.info(f"Created new profile for user {user.email} with role pending")
        
#         return user
    
#     def get_login_redirect_url(self, request):
#         """
#         Custom redirect after social login
#         """
#         # Check if user has a profile
#         if not hasattr(request.user, 'profile'):
#             messages.error(request, 'User profile not found. Please contact admin.')
#             return reverse('login')
        
#         profile = request.user.profile
        
#         # Check if user is approved
#         if not profile.is_approved:
#             messages.warning(request, 'Your account is pending approval. You will be notified when approved.')
#             return reverse('login')
        
#         # Role-based redirection
#         role_redirects = {
#             'admin': 'admin_dashboard',
#             'dept_admin': 'admin_dashboard',
#             'faculty_mentor': 'mentor_dashboard',
#             'evaluator': 'evaluator_dashboard',
#             'hod': 'hod_dashboard',
#             'student': 'student_dashboard',
#         }
        
#         redirect_url = role_redirects.get(profile.role, 'student_dashboard')
#         return reverse(redirect_url)













# apps/authentication/adapter.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

# ✅ Correct import - use UserProfile, not Profile
from apps.authentication.models import UserProfile

import logging
logger = logging.getLogger(__name__)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle Google OAuth login with role-based redirection
    """
    
    def pre_social_login(self, request, sociallogin):
        """Called before social login"""
        email = sociallogin.account.extra_data.get('email')
        if not email:
            messages.error(request, 'Email not found from Google account.')
            return
        
        # Check if user already exists
        try:
            user = User.objects.get(email=email)
            sociallogin.user = user
            logger.info(f"User {email} logged in via Google")
        except User.DoesNotExist:
            logger.info(f"New user {email} signing up via Google")
            pass
        
        return super().pre_social_login(request, sociallogin)
    
    def save_user(self, request, sociallogin, form=None):
        """Save user and create UserProfile"""
        user = super().save_user(request, sociallogin, form)
        
        # Set username if not set
        if not user.username:
            user.username = user.email.split('@')[0]
            user.save()
        
        # ✅ Create UserProfile with pending approval
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'student',  # Default role for new users
                    'is_approved': False,  # Needs admin approval
                    'is_active': True,
                    'phone_number': ''
                }
            )
            if created:
                logger.info(f"Created UserProfile for {user.email} with role student, pending approval")
            else:
                # If profile exists, ensure it's not approved by default
                if profile.is_approved:
                    logger.info(f"User {user.email} already has approved profile")
                else:
                    logger.info(f"User {user.email} has pending approval profile")
        except Exception as e:
            logger.error(f"Error creating UserProfile for {user.email}: {str(e)}")
            # Don't fail the login if profile creation fails
            pass
        
        return user
    
    def get_login_redirect_url(self, request):
        """Custom redirect after social login"""
        if not request.user.is_authenticated:
            return reverse('login')
        
        # Check if user has a profile
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'User profile not found. Please contact admin.')
            return reverse('login')
        
        profile = request.user.profile
        
        # Check if user is active
        if not profile.is_active:
            messages.error(request, 'Your account has been deactivated. Please contact admin.')
            return reverse('login')
        
        # Check if user is approved
        if not profile.is_approved:
            messages.warning(request, 'Your account is pending admin approval. You will be notified when approved.')
            return reverse('login')
        
        # Role-based redirection
        role_redirects = {
            'admin': 'admin_dashboard',
            'dept_admin': 'admin_dashboard',
            'faculty_mentor': 'mentor_dashboard',
            'evaluator': 'evaluator_dashboard',
            'hod': 'hod_dashboard',
            'student': 'student_dashboard',
        }
        
        redirect_url = role_redirects.get(profile.role, 'student_dashboard')
        return reverse(redirect_url)