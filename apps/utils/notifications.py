# Internship-Management-System\apps\utils\notifications.py

from ..models import Notification


def send_notification(recipient, title, message, notification_type='info', link=None):
    """Send a notification to a user"""
    if recipient:
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )


def send_bulk_notification(recipients, title, message, notification_type='info'):
    """Send notification to multiple users"""
    notifications = []
    for recipient in recipients:
        if recipient:
            notifications.append(
                Notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
            )
    if notifications:
        Notification.objects.bulk_create(notifications)