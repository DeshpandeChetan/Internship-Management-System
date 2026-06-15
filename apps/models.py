# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('pending', 'Pending Approval'),
        ('admin', 'System Admin'),
        ('dept_admin', 'Department Admin'),
        ('faculty_mentor', 'Faculty Mentor'),
        ('faculty_evaluator', 'Faculty Evaluator'),
        ('hod', 'HoD/Programme Coordinator'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)


class Programme(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    duration_years = models.IntegerField(default=5)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Batch(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='batches')
    batch_year = models.CharField(max_length=20)  # e.g., "2020-2025"
    academic_year_start = models.IntegerField()
    academic_year_end = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['programme', 'batch_year']
    
    def __str__(self):
        return f"{self.programme.name} - {self.batch_year}"


class Student(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('discontinued', 'Discontinued'),
        ('on_break', 'On Break'),
    )
    
    register_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    mobile = models.CharField(max_length=15, blank=True, null=True)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    degree_start_date = models.DateField()
    degree_end_date = models.DateField()
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.register_number} - {self.name}"
    
    @property
    def current_mentor(self):
        """Get current active mentor"""
        return self.mentor_assignments.filter(effective_to__isnull=True).first()
    
    @property
    def total_internships_completed(self):
        return self.internship_records.filter(completion_status='completed').count()
    
    @property
    def average_internship_marks(self):
        completed_internships = self.internship_records.filter(
            completion_status='completed',
            internship_type='regular'
        )
        marks = [i.viva_marks for i in completed_internships if i.viva_marks]
        if marks:
            return sum(marks) / len(marks)
        return 0


class Organisation(models.Model):
    TYPE_CHOICES = (
        ('advocate', 'Advocate'),
        ('law_firm', 'Law Firm'),
        ('ngo', 'NGO'),
        ('court', 'Court'),
        ('company', 'Company'),
        ('government', 'Government Office'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200)
    organisation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    area_of_work = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='active')
    feedback_rating = models.FloatField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_organisation_type_display()})"
    
    @property
    def student_count(self):
        return self.internship_records.filter(verification_status='verified').count()


class InternshipRecord(models.Model):
    INTERNSHIP_TYPE_CHOICES = (
        ('regular', 'Regular Internship'),
        ('assessment', 'Assessment Internship'),
        ('additional', 'Additional Internship'),
        ('repeated', 'Repeated Internship'),
    )
    
    COMPLETION_STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('not_completed', 'Not Completed'),
        ('repeated', 'Repeated'),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('needs_correction', 'Needs Correction'),
    )
    
    MODE_CHOICES = (
        ('offline', 'Offline'),
        ('online', 'Online'),
        ('hybrid', 'Hybrid'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='internship_records')
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='internship_records')
    internship_type = models.CharField(max_length=20, choices=INTERNSHIP_TYPE_CHOICES, default='regular')
    internship_number = models.IntegerField(null=True, blank=True, help_text="1 to 8 for regular, null for assessment")
    related_semester = models.CharField(max_length=20, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.IntegerField(blank=True, null=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='offline')
    nature_of_work = models.TextField(blank=True, null=True)
    student_submission_date = models.DateTimeField(blank=True, null=True)
    certificate_upload = models.FileField(upload_to='certificates/', blank=True, null=True)
    report_upload = models.FileField(upload_to='reports/', blank=True, null=True)
    completion_status = models.CharField(max_length=20, choices=COMPLETION_STATUS_CHOICES, default='pending')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='draft')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_internships')
    verified_at = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['student', 'internship_number']
    
    def __str__(self):
        return f"{self.student.name} - {self.get_internship_type_display()} {self.internship_number or ''}"
    
    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.duration_days = (self.end_date - self.start_date).days
        super().save(*args, **kwargs)
    
    @property
    def viva_marks(self):
        viva_entry = self.assessment_marks.filter(assessment_type='viva').first()
        return viva_entry.marks_awarded if viva_entry else None
    
    @property
    def intermediate_marks_list(self):
        return self.assessment_marks.filter(assessment_type='intermediate')
    
    @property
    def final_consolidated_score(self):
        # This will be calculated based on configurable rules
        from .utils.calculations import calculate_internship_score
        return calculate_internship_score(self)


class BreakRecord(models.Model):
    BREAK_TYPE_CHOICES = (
        ('academic', 'Academic Break'),
        ('internship', 'Internship Break'),
        ('medical', 'Medical Break'),
        ('other', 'Other'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='breaks')
    break_type = models.CharField(max_length=20, choices=BREAK_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    supporting_document = models.FileField(upload_to='break_documents/', blank=True, null=True)
    impact_on_internship = models.TextField(blank=True, null=True, help_text="How this break affects internship schedule or marks")
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.name} - {self.get_break_type_display()} ({self.start_date} to {self.end_date})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError('End date must be after start date')
        if self.start_date and self.end_date and self.student:
            if self.start_date < self.student.degree_start_date or self.end_date > self.student.degree_end_date:
                raise ValidationError('Break dates must fall within student\'s degree period')


class MentorAssignment(models.Model):
    ASSIGNMENT_LEVEL_CHOICES = (
        ('student', 'Student Level'),
        ('batch', 'Batch Level'),
        ('internship', 'Internship Specific'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='mentor_assignments')
    faculty_mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentor_assignments', limit_choices_to={'role__in': ['faculty_mentor', 'dept_admin']})
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    assignment_level = models.CharField(max_length=20, choices=ASSIGNMENT_LEVEL_CHOICES, default='student')
    related_semester = models.CharField(max_length=20, blank=True, null=True)
    internship_record = models.ForeignKey(InternshipRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentor_assignments')
    reason_for_change = models.TextField(blank=True, null=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_mentors')
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['student', '-effective_from']
    
    def __str__(self):
        return f"{self.student.name} -> {self.faculty_mentor.username} (from {self.effective_from})"
    
    @property
    def is_current(self):
        return self.effective_to is None or self.effective_to >= timezone.now().date()


class AssessmentMarks(models.Model):
    ASSESSMENT_TYPE_CHOICES = (
        ('intermediate', 'Intermediate Assessment'),
        ('report', 'Report Evaluation'),
        ('presentation', 'Presentation/Review'),
        ('mentor', 'Mentor Evaluation'),
        ('viva', 'Final Viva'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('locked', 'Locked'),
    )
    
    internship_record = models.ForeignKey(InternshipRecord, on_delete=models.CASCADE, related_name='assessment_marks')
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPE_CHOICES)
    assessment_name = models.CharField(max_length=100)
    maximum_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    assessment_date = models.DateField(null=True, blank=True)
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessed_marks')
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['internship_record', 'assessment_date', 'assessment_type']
        unique_together = ['internship_record', 'assessment_type', 'assessment_name']
    
    def __str__(self):
        return f"{self.internship_record} - {self.assessment_name} ({self.marks_awarded}/{self.maximum_marks})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.marks_awarded > self.maximum_marks:
            raise ValidationError(f'Marks awarded cannot exceed maximum marks ({self.maximum_marks})')
        if self.marks_awarded < 0:
            raise ValidationError('Marks awarded cannot be negative')


class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = (
        ('certificate', 'Internship Certificate'),
        ('report', 'Internship Report'),
        ('break_approval', 'Break Approval Document'),
        ('evaluation_sheet', 'Evaluation Sheet'),
        ('organisation_confirmation', 'Organisation Confirmation'),
        ('other', 'Other'),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    internship_record = models.ForeignKey(InternshipRecord, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    break_record = models.ForeignKey(BreakRecord, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    verified_at = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student.name} - {self.get_document_type_display()}"


class ApprovalHistory(models.Model):
    ACTION_CHOICES = (
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('locked', 'Locked'),
        ('needs_correction', 'Needs Correction'),
        ('marks_entered', 'Marks Entered'),
        ('marks_updated', 'Marks Updated'),
    )
    
    internship_record = models.ForeignKey(InternshipRecord, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_history')
    assessment_marks = models.ForeignKey(AssessmentMarks, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_actions')
    previous_status = models.CharField(max_length=50, blank=True, null=True)
    new_status = models.CharField(max_length=50, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Approval Histories'
    
    def __str__(self):
        return f"{self.action} by {self.performed_by.username} at {self.timestamp}"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"


class AssessmentConfiguration(models.Model):
    """Configurable assessment rules"""
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='assessment_configs')
    regular_internship_count = models.IntegerField(default=8)
    assessment_internship_enabled = models.BooleanField(default=True)
    assessment_internship_duration_months = models.IntegerField(default=3)
    include_intermediate_marks = models.BooleanField(default=False)
    calculation_formula = models.CharField(max_length=50, default='simple_average',
                                           choices=(
                                               ('simple_average', 'Simple Average'),
                                               ('weighted_average', 'Weighted Average'),
                                               ('best_n', 'Best N Internships'),
                                               ('all_with_assessment', 'All Internships + Assessment'),
                                               ('separate_components', 'Separate Components'),
                                           ))
    best_n_value = models.IntegerField(default=5, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.programme.name} Assessment Config"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    link = models.CharField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"