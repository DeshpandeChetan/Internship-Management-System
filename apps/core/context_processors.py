# apps/core/context_processors.py


def notifications(request):
    """Expose the current user's unread notifications to every template (navbar bell icon)."""
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        unread = user.notifications.filter(is_read=False)
        return {
            'unread_notifications_count': unread.count(),
            'unread_notifications': unread[:8],
        }
    return {
        'unread_notifications_count': 0,
        'unread_notifications': [],
    }
