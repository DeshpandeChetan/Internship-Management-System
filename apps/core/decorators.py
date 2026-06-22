# from django.shortcuts import redirect
# from django.contrib import messages
# from functools import wraps
# from django.contrib.auth.decorators import user_passes_test
# from apps.utils.permissions import is_admin, is_hod, is_faculty_mentor, is_faculty_evaluator, is_student

# def role_required(allowed_roles=[]):
#     """
#     Decorator to check if user has required role.
#     Usage: @role_required(['admin', 'dept_admin'])
#     """
#     def decorator(view_func):
#         @wraps(view_func)
#         def wrapper(request, *args, **kwargs):
#             if not request.user.is_authenticated:
#                 messages.error(request, 'Please login first.')
#                 return redirect('login')
            
#             # Check if user has a profile with role
#             if not hasattr(request.user, 'profile'):
#                 messages.error(request, 'User profile not found.')
#                 return redirect('login')
            
#             user_role = request.user.profile.role
            
#             # Check if user's role is allowed
#             if allowed_roles and user_role not in allowed_roles:
#                 messages.error(request, f'You do not have permission to access this page. Required roles: {", ".join(allowed_roles)}')
#                 return redirect('dashboard')
            
#             return view_func(request, *args, **kwargs)
#         return wrapper
#     return decorator

# # def admin_required(view_func):
# #     """Decorator for admin-only views"""
# #     return role_required(['admin'])(view_func)
# def admin_required(view_func):
#     """Decorator for system admin"""
#     return user_passes_test(is_admin)(view_func)

# # def dept_admin_required(view_func):
# #     """Decorator for department admin views"""
# #     return role_required(['admin', 'dept_admin'])(view_func)
# def dept_admin_required(view_func):
#     """Decorator for department admin (now HOD)"""
#     return user_passes_test(is_hod)(view_func)

# def mentor_required(view_func):
#     """Decorator for mentor views"""
#     return role_required(['admin', 'dept_admin', 'faculty_mentor'])(view_func)

# def evaluator_required(view_func):
#     """Decorator for evaluator views"""
#     return role_required(['admin', 'dept_admin', 'evaluator'])(view_func)

# # def hod_required(view_func):
# #     """Decorator for HOD views"""
# #     return role_required(['admin', 'hod'])(view_func)
# def hod_required(view_func):
#     """Decorator for HOD"""
#     return user_passes_test(is_hod)(view_func)

# def student_required(view_func):
#     """Decorator for student views"""
#     return role_required(['student'])(view_func)

# def login_required(view_func):
#     """Custom login required decorator with redirect"""
#     @wraps(view_func)
#     def wrapper(request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             messages.error(request, 'Please login first.')
#             return redirect('login')
#         return view_func(request, *args, **kwargs)
#     return wrapper























# apps/core/decorators.py

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

# Import from utils.permissions
from apps.utils.permissions import (
    is_admin, is_hod, is_dept_admin, 
    is_faculty_mentor, is_faculty_evaluator, is_student
)


def admin_required(view_func):
    """Decorator for system admin only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_admin(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    return wrapper


def hod_required(view_func):
    """Decorator for HOD only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_hod(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'HOD access required.')
        return redirect('dashboard')
    return wrapper


def dept_admin_required(view_func):
    """Decorator for department admin (merged with HOD)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_dept_admin(request.user):  # Now checks for HOD
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Department admin access required.')
        return redirect('dashboard')
    return wrapper


def mentor_required(view_func):
    """Decorator for faculty mentor"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_faculty_mentor(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Faculty mentor access required.')
        return redirect('dashboard')
    return wrapper


def evaluator_required(view_func):
    """Decorator for faculty evaluator"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_faculty_evaluator(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Faculty evaluator access required.')
        return redirect('dashboard')
    return wrapper


def student_required(view_func):
    """Decorator for student"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_student(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Student access required.')
        return redirect('dashboard')
    return wrapper


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