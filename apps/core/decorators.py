from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles=[]):
    """
    Decorator to check if user has required role.
    Usage: @role_required(['admin', 'dept_admin'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please login first.')
                return redirect('login')
            
            # Check if user has a profile with role
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'User profile not found.')
                return redirect('login')
            
            user_role = request.user.profile.role
            
            # Check if user's role is allowed
            if allowed_roles and user_role not in allowed_roles:
                messages.error(request, f'You do not have permission to access this page. Required roles: {", ".join(allowed_roles)}')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def admin_required(view_func):
    """Decorator for admin-only views"""
    return role_required(['admin'])(view_func)

def dept_admin_required(view_func):
    """Decorator for department admin views"""
    return role_required(['admin', 'dept_admin'])(view_func)

def mentor_required(view_func):
    """Decorator for mentor views"""
    return role_required(['admin', 'dept_admin', 'faculty_mentor'])(view_func)

def evaluator_required(view_func):
    """Decorator for evaluator views"""
    return role_required(['admin', 'dept_admin', 'evaluator'])(view_func)

def hod_required(view_func):
    """Decorator for HOD views"""
    return role_required(['admin', 'hod'])(view_func)

def student_required(view_func):
    """Decorator for student views"""
    return role_required(['student'])(view_func)

def login_required(view_func):
    """Custom login required decorator with redirect"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper