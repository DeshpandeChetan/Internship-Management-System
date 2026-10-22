from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.authentication.models import UserProfile
from apps.authentication.permissions import is_admin
from . import models as domain
from .audit import log_action
from .permanent_deletion import delete_preserving_history


RECORD_TYPES = {model._meta.model_name: model for model in (
    UserProfile, domain.Department, domain.Programme, domain.Batch, domain.Student,
    domain.Organisation, domain.InternshipRecord, domain.BreakRecord,
    domain.MentorAssignment, domain.AssessmentComponent, domain.AssessmentMarks,
    domain.AssessmentConfiguration,
)}


def _record(kind, pk):
    model = RECORD_TYPES.get(kind)
    if model is None:
        raise Http404
    return get_object_or_404(model.all_objects.select_for_update(), pk=pk, deleted_at__isnull=False, is_history_reference=False)


@login_required
@user_passes_test(is_admin)
def settings_page(request):
    return render(request, 'admin/recycle_settings.html', {'active_tab': 'admin_settings'})


@login_required
@user_passes_test(is_admin)
def deleted_content(request):
    records = []
    for kind, model in RECORD_TYPES.items():
        for record in model.all_objects.filter(deleted_at__isnull=False, is_history_reference=False):
            fields = []
            for field in record._meta.fields:
                if field.name in ('deleted_by', 'deleted_at', 'is_history_reference'):
                    continue
                value = getattr(record, field.name)
                if field.choices:
                    value = getattr(record, f'get_{field.name}_display')()
                fields.append((field.verbose_name, str(value) if value is not None else '-'))
            records.append({'kind': kind, 'record': record, 'label': model._meta.verbose_name,
                            'fields': fields})
    records.sort(key=lambda item: item['record'].deleted_at, reverse=True)
    return render(request, 'admin/deleted_content.html', {'records': records, 'active_tab': 'admin_settings'})


@login_required
@user_passes_test(is_admin)
@require_POST
@transaction.atomic
def restore_record(request, kind, pk):
    record = _record(kind, pk)
    for field in record._meta.fields:
        if isinstance(field, models.ForeignKey) and field.name != 'deleted_by' and getattr(record, field.attname):
            parent = getattr(record, field.name)
            if getattr(parent, 'deleted_at', None) and not getattr(parent, 'is_history_reference', False):
                messages.error(request, f'Restore the related {field.verbose_name} first.')
                return redirect('admin_deleted_content')
    type(record).all_objects.filter(pk=record.pk).update(deleted_at=None, deleted_by=None)
    log_action(request, 'UPDATE', 'DeletedContent', record_id=pk, new_value=f'Restored {kind}')
    messages.success(request, 'Record restored to its original module with its previous status.')
    return redirect('admin_deleted_content')


@login_required
@user_passes_test(is_admin)
@require_POST
@transaction.atomic
def permanently_delete(request, kind, pk):
    record = _record(kind, pk)
    if isinstance(record, UserProfile):
        if record.user_id == request.user.pk or record.user.is_superuser:
            messages.error(request, 'This administrator account is protected.')
            return redirect('admin_deleted_content')
    log_action(request, 'DELETE', 'DeletedContent', record_id=pk, old_value=f'Permanently deleted {kind}: {record}')
    delete_preserving_history(record)
    messages.success(request, 'Record permanently deleted. Related historical records have been preserved.')
    return redirect('admin_deleted_content')
