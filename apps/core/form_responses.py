from django.http import JsonResponse
from django.shortcuts import render


def invalid_form_response(request, form):
    """Keep bound forms available and return field errors to the shared handler."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    extra_fields = [(key, value) for key, values in request.POST.lists()
                    if key not in form.fields and key != 'csrfmiddlewaretoken'
                    for value in values]
    return render(request, 'includes/invalid_form_page.html', {
        'form': form, 'extra_fields': extra_fields,
    }, status=400)
