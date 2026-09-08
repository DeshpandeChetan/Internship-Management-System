# apps/utils/audit.py

import logging

logger = logging.getLogger(__name__)

try:
    from apps.core.models import AuditLog
except ImportError:
    AuditLog = None
    logger.warning("AuditLog model not found in apps.core.models")


def get_client_ip(request):
    """Best-effort client IP extraction, honoring a reverse proxy's X-Forwarded-For."""
    if not request:
        return None
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(request, action, module, record_id='', old_value='', new_value=''):
    """
    Write one AuditLog entry for a user-initiated action in the live application.

    Safe to call from any view: never raises, and is a no-op if there is no
    authenticated user on the request (e.g. anonymous/system context).
    """
    if AuditLog is None:
        return
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            module=module,
            record_id=str(record_id) if record_id else '',
            old_value=str(old_value) if old_value else '',
            new_value=str(new_value) if new_value else '',
            ip_address=get_client_ip(request),
        )
    except Exception as exc:
        logger.error(f"Error writing audit log: {exc}")
