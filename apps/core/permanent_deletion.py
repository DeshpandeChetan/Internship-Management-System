"""Remove selected records while retaining required historical relationships."""
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def _related(record, excluded=()):
    for relation in record._meta.related_objects:
        if relation.related_model in excluded or relation.many_to_many:
            continue
        records = relation.related_model._base_manager.filter(**{relation.field.name: record})
        if records.exists():
            yield relation.field, records


def _history_reference(record, **overrides):
    token = uuid.uuid4()
    values = {field.attname: getattr(record, field.attname) for field in record._meta.concrete_fields
              if not field.primary_key}
    values.update(is_history_reference=True, deleted_at=timezone.now(), deleted_by_id=None)
    for field in record._meta.concrete_fields:
        if field.primary_key:
            continue
        if field.unique:
            if field.is_relation:
                if field.null:
                    values[field.attname] = None
            elif isinstance(field, models.CharField):
                if field.name == 'name':
                    suffix = f' ({token.hex[:8]})'
                    value = ('[Deleted] ' + str(getattr(record, field.attname)))[:field.max_length - len(suffix)] + suffix
                else:
                    value = f'deleted-{token.hex}@invalid.example' if isinstance(field, models.EmailField) else f'deleted-{token.hex}'
                values[field.attname] = value[:field.max_length]
    if hasattr(record, 'internship_number'):
        values['internship_number'] = f'deleted-{token.hex[:12]}'
    for field in record._meta.concrete_fields:
        if field.name in ('is_active', 'is_approved'):
            values[field.name] = False
        if isinstance(field, models.FileField):
            values[field.attname] = ''
    values.update(overrides)
    reference = type(record)(**values)
    # Bypass domain save hooks: references must not create accounts or approvals.
    models.Model.save(reference, force_insert=True)
    return reference


def _detach(record, *, excluded=(), reference=None):
    for field, records in _related(record, excluded):
        if reference is None:
            reference = _history_reference(record)
        records.update(**{field.attname: reference.pk})
    return reference


def delete_preserving_history(record):
    from apps.authentication.models import UserProfile
    from .models import Student

    if isinstance(record, UserProfile):
        user = User.objects.select_for_update().get(pk=record.user_id)
        if user.is_superuser:
            raise ValueError('Administrator accounts are protected.')
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount
        user_reference = None
        profile_dependents = list(_related(record))
        user_dependents = list(_related(user, (UserProfile, EmailAddress, SocialAccount)))
        if profile_dependents or user_dependents:
            token = uuid.uuid4().hex
            user_reference = User(username=f'deleted-{token}', email='', first_name='Deleted',
                                  last_name='User', is_active=False)
            user_reference.set_unusable_password()
            user_reference.save()
            if profile_dependents:
                profile_reference = _history_reference(record, user_id=user_reference.pk)
                _detach(record, reference=profile_reference)
            else:
                UserProfile.all_objects.create(user=user_reference, role='unassigned', is_active=False,
                    is_approved=False, is_history_reference=True, deleted_at=timezone.now())
        else:
            _detach(record)
        for field, records in user_dependents:
            records.update(**{field.attname: user_reference.pk})
        models.Model.delete(user)
        return

    if isinstance(record, Student) and record.user_id:
        UserProfile.all_objects.filter(user_id=record.user_id, role='student').update(is_active=False)
    _detach(record)
    models.Model.delete(record)
