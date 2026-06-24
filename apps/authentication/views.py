from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from .models import UserProfile


def redirect_to_role_dashboard(request):
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'User profile not found. Please contact admin.')
        return redirect('login')

    profile = request.user.profile
    if not profile.is_approved:
        messages.warning(request, 'Your account is pending admin approval.')
        return render(request, 'accounts/pending_approval.html', {'hide_sidebar': True})

    dashboard_urls = {
        'admin': 'admin_dashboard',
        'hod': 'hod_dashboard',
        'faculty_mentor': 'mentor_dashboard',
        'evaluator': 'evaluator_dashboard',
        'student': 'student_dashboard',
    }
    return redirect(dashboard_urls.get(profile.role, 'student_dashboard'))


def login_view(request):
    if request.user.is_authenticated:
        return redirect_to_role_dashboard(request)
    return render(request, 'authentication/login.html')

# @login_required
# def profile_view(request):
#     return render(request, 'authentication/profile.html', {'user': request.user})

@login_required
def dashboard_view(request):
    return redirect_to_role_dashboard(request)

def logout_view(request):
    logout(request)
    return redirect('login')
