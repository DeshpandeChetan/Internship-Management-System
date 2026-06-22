# Internship-Management-System\apps\context_processors.py
from django.conf import settings


def site_settings(request):
    """Add site-wide settings to templates"""
    return {
        'SITE_NAME': 'Internship Management System',
        'SITE_VERSION': '1.0.0',
        'COMPANY_NAME': 'Internship Cell',
    }


def user_notifications(request):
    """Add user notifications to templates"""
    if request.user.is_authenticated:
        notifications = request.user.notifications.filter(is_read=False)
        return {
            'unread_notifications_count': notifications.count(),
            'unread_notifications': notifications[:5]
        }
    return {
        'unread_notifications_count': 0,
        'unread_notifications': []
    }


# Add this function - it might be what your settings is looking for
def site_context(request):
    """Combined site context for templates"""
    context = site_settings(request)
    context.update(user_notifications(request))
    return context