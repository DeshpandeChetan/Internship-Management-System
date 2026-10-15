from django.contrib import messages
from django.http import JsonResponse


class FormSubmissionMiddleware:
    """Return legacy business-validation messages to the submitting form."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (request.method != 'POST' or request.headers.get('X-IMS-Form') != '1'
                or not request.user.is_authenticated or response.status_code not in (301, 302, 303)):
            return response
        storage = messages.get_messages(request)
        queued = list(storage)
        failures = [item for item in queued if item.level >= messages.ERROR]
        if not failures:
            storage.used = False
            return response
        for item in queued:
            if item.level < messages.ERROR:
                messages.add_message(request, item.level, item.message, extra_tags=item.extra_tags)
        errors = {}
        for item in failures:
            field, separator, message = str(item).partition(': ')
            key = field if separator and field in request.POST else '__all__'
            errors.setdefault(key, []).append(message if key != '__all__' else str(item))
        return JsonResponse({'success': False, 'errors': errors}, status=400)
