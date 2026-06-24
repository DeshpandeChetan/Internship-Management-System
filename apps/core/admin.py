from django.contrib import admin

from .models import (
    AssessmentComponent,
    AssessmentConfiguration,
    AssessmentMarks,
    AssessmentMarksHistory,
    AuditLog,
    Batch,
    BreakRecord,
    ConsolidatedScore,
    Department,
    InternshipRecord,
    MentorAssignment,
    Notification,
    Organisation,
    Programme,
    Student,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_on', 'updated_on')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    list_editable = ('is_active',)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'duration_years', 'is_active', 'created_on')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    list_editable = ('is_active',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'programme', 'start_year', 'end_year', 'is_active', 'created_on')
    list_filter = ('programme', 'is_active', 'start_year', 'end_year')
    search_fields = ('name', 'programme__name', 'programme__code')
    list_editable = ('is_active',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'register_number', 'name', 'email', 'department', 'programme', 'batch',
        'degree_start_date', 'degree_end_date', 'status', 'created_on',
    )
    list_filter = ('department', 'programme', 'batch', 'status')
    search_fields = ('register_number', 'name', 'email', 'mobile')
    raw_id_fields = ('user', 'created_by')
    date_hierarchy = 'created_on'
    readonly_fields = ('created_on', 'updated_on')


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'organisation_type', 'organisation_type_other', 'city', 'state',
        'email', 'phone', 'is_active', 'updated_on',
    )
    list_filter = ('organisation_type', 'is_active', 'city', 'state')
    search_fields = (
        'name', 'organisation_type_other', 'contact_person', 'email', 'phone',
        'city', 'state', 'area_of_work',
    )
    list_editable = ('is_active',)
    readonly_fields = ('created_on', 'updated_on')


@admin.register(InternshipRecord)
class InternshipRecordAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'organisation', 'internship_type', 'internship_number',
        'academic_phase', 'start_date', 'end_date', 'completion_status',
        'verification_status', 'date_override_approved', 'verified_by', 'submission_date',
    )
    list_filter = (
        'internship_type', 'completion_status', 'verification_status', 'mode',
        'date_override_approved',
        'academic_phase', 'related_semester',
    )
    search_fields = (
        'student__register_number', 'student__name', 'student__email',
        'organisation__name', 'internship_number', 'academic_phase',
    )
    raw_id_fields = ('student', 'organisation', 'created_by', 'updated_by', 'verified_by')
    date_hierarchy = 'created_on'
    readonly_fields = ('created_on', 'updated_on', 'verified_at')


@admin.register(BreakRecord)
class BreakRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'break_type', 'start_date', 'end_date', 'approved_by', 'created_on')
    list_filter = ('break_type', 'start_date', 'end_date')
    search_fields = ('student__register_number', 'student__name', 'reason', 'remarks')
    raw_id_fields = ('student', 'approved_by')
    date_hierarchy = 'created_on'
    readonly_fields = ('created_on', 'updated_on')


@admin.register(MentorAssignment)
class MentorAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'faculty_mentor', 'effective_from', 'effective_to',
        'assignment_level', 'related_semester', 'is_active', 'assigned_by',
    )
    list_filter = ('assignment_level', 'is_active', 'effective_from', 'effective_to')
    search_fields = (
        'student__register_number', 'student__name',
        'faculty_mentor__user__email', 'faculty_mentor__user__first_name',
        'faculty_mentor__user__last_name', 'related_semester',
    )
    raw_id_fields = ('student', 'faculty_mentor', 'internship_record', 'assigned_by')
    date_hierarchy = 'created_on'
    readonly_fields = ('created_on', 'updated_on')


@admin.register(AssessmentComponent)
class AssessmentComponentAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'assessment_type', 'default_max_marks', 'weightage',
        'is_mandatory', 'is_active', 'created_on',
    )
    list_filter = ('assessment_type', 'is_mandatory', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active',)


@admin.register(AssessmentMarks)
class AssessmentMarksAdmin(admin.ModelAdmin):
    list_display = (
        'internship_record', 'assessment_component', 'assessment_name',
        'marks_awarded', 'maximum_marks', 'weightage', 'assessment_date',
        'status', 'evaluator', 'locked_by',
    )
    list_filter = ('assessment_component__assessment_type', 'status', 'assessment_date')
    search_fields = (
        'assessment_name', 'internship_record__student__register_number',
        'internship_record__student__name', 'internship_record__organisation__name',
    )
    raw_id_fields = ('internship_record', 'assessment_component', 'evaluator', 'locked_by')
    date_hierarchy = 'created_on'
    readonly_fields = ('created_on', 'updated_on', 'locked_at')


@admin.register(AssessmentMarksHistory)
class AssessmentMarksHistoryAdmin(admin.ModelAdmin):
    list_display = ('assessment_marks', 'edited_by', 'edited_on', 'remarks')
    list_filter = ('edited_on',)
    search_fields = (
        'assessment_marks__assessment_name',
        'assessment_marks__internship_record__student__register_number',
        'assessment_marks__internship_record__student__name',
        'edited_by__email',
    )
    raw_id_fields = ('assessment_marks', 'edited_by')
    readonly_fields = ('old_values', 'new_values', 'edited_on')


@admin.register(ConsolidatedScore)
class ConsolidatedScoreAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'regular_internship_average', 'assessment_internship_score',
        'final_consolidated_score', 'calculation_formula', 'is_finalized', 'finalized_by',
    )
    list_filter = ('calculation_formula', 'is_finalized')
    search_fields = ('student__register_number', 'student__name')
    raw_id_fields = ('student', 'finalized_by')
    readonly_fields = ('created_on', 'updated_on', 'finalized_at')


@admin.register(AssessmentConfiguration)
class AssessmentConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'programme', 'regular_internship_count', 'assessment_internship_enabled',
        'include_intermediate_marks', 'calculation_formula', 'best_n_value',
        'is_active',
    )
    list_filter = ('programme', 'calculation_formula', 'is_active')
    search_fields = ('programme__name', 'programme__code')
    list_editable = ('is_active',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'recipient__username', 'title', 'message')
    raw_id_fields = ('recipient',)
    date_hierarchy = 'created_at'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'module', 'record_id', 'ip_address', 'timestamp')
    list_filter = ('action', 'module', 'timestamp')
    search_fields = ('user__email', 'user__username', 'action', 'module', 'record_id')
    raw_id_fields = ('user',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
