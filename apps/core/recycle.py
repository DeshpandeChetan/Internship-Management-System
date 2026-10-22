from django.conf import settings
from django.db import models
from django.utils import timezone


class RecycleQuerySet(models.QuerySet):
    def delete(self):
        count = self.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        return count, {self.model._meta.label: count}


class ActiveRecordManager(models.Manager.from_queryset(RecycleQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True, is_history_reference=False)


class RecyclableModel(models.Model):
    is_history_reference = models.BooleanField(default=False, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   editable=False, related_name='+', on_delete=models.SET_NULL)
    objects = ActiveRecordManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = 'all_objects'
        default_manager_name = 'objects'

    def delete(self, using=None, keep_parents=False, *, deleted_by=None):
        now = timezone.now()
        count = type(self).all_objects.using(using or self._state.db).filter(
            pk=self.pk, deleted_at__isnull=True,
        ).update(deleted_at=now, deleted_by=deleted_by)
        if count:
            self.deleted_at = now
            self.deleted_by = deleted_by
        return count, {self._meta.label: count}
