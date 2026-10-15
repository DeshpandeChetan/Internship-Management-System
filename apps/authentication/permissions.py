# apps/authentication/permissions.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def is_admin(user):
    """Check if user is system admin"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role == 'admin'
    return False

def is_hod(user):
    """Check if user is HoD/Coordinator"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role == 'hod'  # ← HOD role
    return False

def is_dept_admin(user):
    """Check if user is department admin (merged with hod)"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role == 'hod'  # ← Now HOD handles department admin duties
    return False


def is_faculty_mentor(user):
    """Check if user is faculty mentor"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role in ['faculty_mentor', 'hod', 'admin']
    return False


def is_faculty_evaluator(user):
    """Check if user is faculty evaluator"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role in ['evaluator', 'faculty_evaluator', 'hod', 'admin']
    return False

def is_student(user):
    """Check if user is student"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role == 'student'
    return False

def role_required(allowed_roles=[]):
    """Decorator to check if user has required role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if hasattr(request.user, 'profile') and request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        return wrapper
    return decorator
