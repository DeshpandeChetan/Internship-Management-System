# # Internship-Management-System\apps\utils\notifications.py

# from ..models import Notification


# def send_notification(recipient, title, message, notification_type='info', link=None):
#     """Send a notification to a user"""
#     if recipient:
#         Notification.objects.create(
#             recipient=recipient,
#             title=title,
#             message=message,
#             notification_type=notification_type,
#             link=link
#         )


# def send_bulk_notification(recipients, title, message, notification_type='info'):
#     """Send notification to multiple users"""
#     notifications = []
#     for recipient in recipients:
#         if recipient:
#             notifications.append(
#                 Notification(
#                     recipient=recipient,
#                     title=title,
#                     message=message,
#                     notification_type=notification_type
#                 )
#             )
#     if notifications:
#         Notification.objects.bulk_create(notifications)



# apps/utils/notifications.py

import logging
logger = logging.getLogger(__name__)

# Try to import Notification from core.models
try:
    from apps.core.models import Notification
except ImportError:
    Notification = None
    logger.warning("Notification model not found in apps.core.models")


def send_notification(recipient, title, message, notification_type='info', link=None):
    """Send a notification to a user"""
    if Notification and recipient:
        try:
            Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link
            )
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    else:
        logger.info(f"Notification: {title} - {message} (to {recipient})")


def send_bulk_notification(recipients, title, message, notification_type='info'):
    """Send notification to multiple users"""
    if Notification and recipients:
        try:
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
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
    else:
        logger.info(f"Bulk Notification: {title} - {message} (to {len(recipients) if recipients else 0} users)")