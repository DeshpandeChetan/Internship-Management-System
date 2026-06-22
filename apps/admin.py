# Internship-Management-System\apps\admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Student, Organisation, InternshipRecord, BreakRecord,
    MentorAssignment, AssessmentMarks, Document, Programme, Batch,
    AssessmentConfiguration, ApprovalHistory, AuditLog, Notification
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'profile_picture', 'employee_id')}),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('register_number', 'name', 'programme', 'batch', 'current_status', 'degree_start_date', 'degree_end_date')
    list_filter = ('programme', 'batch', 'current_status')
    search_fields = ('register_number', 'name', 'email')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation_type', 'city', 'status', 'student_count')
    list_filter = ('organisation_type', 'status', 'city')
    search_fields = ('name', 'contact_person', 'email', 'phone')


@admin.register(InternshipRecord)
class InternshipRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'organisation', 'internship_type', 'internship_number', 'start_date', 'end_date', 'verification_status')
    list_filter = ('internship_type', 'verification_status', 'completion_status', 'mode')
    search_fields = ('student__name', 'student__register_number', 'organisation__name')
    raw_id_fields = ('student', 'organisation', 'verified_by')
    date_hierarchy = 'created_at'


@admin.register(BreakRecord)
class BreakRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'break_type', 'start_date', 'end_date')
    list_filter = ('break_type',)
    search_fields = ('student__name', 'student__register_number')
    date_hierarchy = 'created_at'


@admin.register(MentorAssignment)
class MentorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'faculty_mentor', 'effective_from', 'effective_to', 'is_current')
    list_filter = ('assignment_level',)
    search_fields = ('student__name', 'faculty_mentor__username')
    raw_id_fields = ('student', 'faculty_mentor', 'assigned_by', 'internship_record')


@admin.register(AssessmentMarks)
class AssessmentMarksAdmin(admin.ModelAdmin):
    list_display = ('internship_record', 'assessment_type', 'assessment_name', 'marks_awarded', 'maximum_marks', 'status', 'evaluator')
    list_filter = ('assessment_type', 'status')
    search_fields = ('internship_record__student__name', 'assessment_name')
    raw_id_fields = ('internship_record', 'evaluator')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('student', 'document_type', 'verification_status', 'uploaded_at')
    list_filter = ('document_type', 'verification_status')
    search_fields = ('student__name',)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'duration_years', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_year', 'programme', 'academic_year_start', 'academic_year_end', 'is_active')
    list_filter = ('programme', 'is_active')
    search_fields = ('batch_year',)


@admin.register(AssessmentConfiguration)
class AssessmentConfigurationAdmin(admin.ModelAdmin):
    list_display = ('programme', 'regular_internship_count', 'calculation_formula', 'is_active')
    list_filter = ('programme', 'calculation_formula', 'is_active')


@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ('action', 'performed_by', 'timestamp')
    list_filter = ('action',)
    search_fields = ('performed_by__username',)
    date_hierarchy = 'timestamp'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'module', 'timestamp')
    list_filter = ('action', 'module')
    search_fields = ('user__username',)
    date_hierarchy = 'timestamp'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title')