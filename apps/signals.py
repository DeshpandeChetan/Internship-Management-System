# signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    User, Student, InternshipRecord, AssessmentMarks,
    ApprovalHistory, AuditLog
)


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Create student profile when user with student role is created"""
    if created and instance.role == 'student':
        # Student profile needs to be created separately by admin
        pass


@receiver(pre_save, sender=InternshipRecord)
def log_internship_change(sender, instance, **kwargs):
    """Log changes to internship records"""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            changes = []
            
            if old.verification_status != instance.verification_status:
                changes.append(f"Status changed from {old.verification_status} to {instance.verification_status}")
            
            if changes:
                AuditLog.objects.create(
                    user=instance.verified_by or (instance.student.user if hasattr(instance.student, 'user') else None),
                    action='UPDATE',
                    module='InternshipRecord',
                    record_id=instance.id,
                    old_value=str(old.verification_status),
                    new_value=str(instance.verification_status)
                )
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=AssessmentMarks)
def create_approval_history(sender, instance, created, **kwargs):
    """Create approval history entry when marks are saved"""
    if created:
        ApprovalHistory.objects.create(
            assessment_marks=instance,
            action='marks_entered',
            performed_by=instance.evaluator,
            new_status=instance.status
        )
    elif instance.status == 'approved':
        ApprovalHistory.objects.create(
            assessment_marks=instance,
            action='approved',
            performed_by=instance.evaluator,
            previous_status='submitted',
            new_status='approved'
        )
    elif instance.status == 'locked':
        ApprovalHistory.objects.create(
            assessment_marks=instance,
            action='locked',
            performed_by=instance.evaluator,
            previous_status='approved',
            new_status='locked'
        )


@receiver(post_save, sender=InternshipRecord)
def create_internship_approval_history(sender, instance, created, **kwargs):
    """Create approval history for internship record changes"""
    if created:
        ApprovalHistory.objects.create(
            internship_record=instance,
            action='created',
            performed_by=instance.student.user if hasattr(instance.student, 'user') and instance.student.user else None,
            new_status=instance.verification_status
        )
    elif instance.verification_status == 'submitted':
        ApprovalHistory.objects.create(
            internship_record=instance,
            action='submitted',
            performed_by=instance.student.user if hasattr(instance.student, 'user') and instance.student.user else None,
            previous_status='draft',
            new_status='submitted'
        )
    elif instance.verification_status == 'verified':
        ApprovalHistory.objects.create(
            internship_record=instance,
            action='verified',
            performed_by=instance.verified_by,
            previous_status='submitted',
            new_status='verified'
        )