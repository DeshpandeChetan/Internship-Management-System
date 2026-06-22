# Internship-Management-System\apps\pipeline.py
from django.shortcuts import redirect
from django.contrib import messages

def assign_default_role(strategy, details, user=None, *args, **kwargs):
    """Assign role based on email domain or mark as unassigned"""
    if user and not user.role:
        # Check if user is in allowed list or has specific email domain
        # For now, set as 'pending' - admin must assign role
        user.role = 'pending'
        user.is_active = False  # Inactive until admin assigns role
        user.save()
        
        # Notify admin about new user (you can implement email notification)
        
    return {'user': user}