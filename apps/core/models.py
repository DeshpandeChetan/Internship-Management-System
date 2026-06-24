#Internship-Management-System\apps\core\models.py
import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.authentication.models import UserProfile

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Programme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    duration_years = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Batch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='batches')
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.programme.code})"

# apps/core/models.py (Only the Student model part)

# apps/core/models.py (Student model only - FIXED)

class Student(models.Model):
    """
    Student model as per SRS - Direct fields, optional User link for Google Login
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_break', 'On Break'),
        ('discontinued', 'Discontinued'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Direct fields from SRS
    register_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=250)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=20, blank=True)
    
    # Relationships
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    
    # Degree dates
    degree_start_date = models.DateField(null=True, blank=True)
    degree_end_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    remarks = models.TextField(blank=True)
    
    # Optional: Link to User for Google Login
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='student_profile'
    )
    
    # Tracking
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_students'
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.register_number} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Auto-create User if doesn't exist (no password for Google Login)
        if not self.user:
            user, created = User.objects.get_or_create(
                email=self.email,
                defaults={
                    'username': self.email,
                    'first_name': self.name.split()[0] if ' ' in self.name else self.name,
                    'last_name': ' '.join(self.name.split()[1:]) if ' ' in self.name else '',
                }
            )
            # No password set - Google Login handles authentication
            if created:
                user.save()
            self.user = user
        
        # Create UserProfile for role-based access
        if self.user:
            profile, created = UserProfile.objects.get_or_create(
                user=self.user,
                defaults={
                    'role': 'student',
                    'phone_number': self.mobile or '',
                    'is_active': True,
                    'is_approved': True
                }
            )
            if not created:
                profile.role = 'student'
                profile.department = self.department
                profile.phone_number = self.mobile or ''
                profile.is_approved = True
                profile.save()
        
        super().save(*args, **kwargs)

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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=250, unique=True)
    organisation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    organisation_type_other = models.CharField(max_length=100, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    area_of_work = models.TextField(blank=True)
    feedback_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    remarks = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.type_display})"

    @property
    def type_display(self):
        if self.organisation_type == 'other' and self.organisation_type_other:
            return f"Other / {self.organisation_type_other}"
        return self.get_organisation_type_display()

class InternshipRecord(models.Model):
    INTERNSHIP_TYPES = (
        ('regular', 'Regular Internship'),
        ('assessment', 'Assessment Internship'),
        ('additional', 'Additional Internship'),
        ('repeated', 'Repeated Internship'),
    )
    
    COMPLETION_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('not_completed', 'Not Completed'),
        ('repeated', 'Repeated'),
    )
    
    VERIFICATION_STATUS = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('needs_correction', 'Needs Correction'),
        ('rejected', 'Rejected'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='internships')
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='internships')
    internship_type = models.CharField(max_length=20, choices=INTERNSHIP_TYPES, default='regular')
    internship_number = models.CharField(max_length=20, help_text="1-8 or Assessment")
    related_semester = models.CharField(max_length=50, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    mode = models.CharField(max_length=20, choices=(('offline', 'Offline'), ('online', 'Online'), ('hybrid', 'Hybrid')), default='offline')
    academic_phase = models.CharField(max_length=50, blank=True)
    nature_of_work = models.TextField(blank=True)
    supporting_document = models.FileField(upload_to='internship_documents/', blank=True, null=True)
    certificate_upload = models.FileField(upload_to='internship_certificates/', blank=True, null=True)
    report_upload = models.FileField(upload_to='internship_reports/', blank=True, null=True)
    date_override_approved = models.BooleanField(default=False)
    date_override_reason = models.TextField(blank=True)
    submission_date = models.DateField(null=True, blank=True)
    completion_status = models.CharField(max_length=20, choices=COMPLETION_STATUS, default='pending')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='draft')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_internships')
    verified_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_internships')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_internships')
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    @property
    def duration(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    @property
    def overlapping_breaks(self):
        if not self.start_date or not self.end_date:
            return BreakRecord.objects.none()
        return self.student.breaks.filter(
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )

    @property
    def has_break_overlap(self):
        return self.overlapping_breaks.exists()
    
    def __str__(self):
        return f"{self.student.register_number} - {self.internship_type} #{self.internship_number}"

class BreakRecord(models.Model):
    BREAK_TYPES = (
        ('academic', 'Academic Break'),
        ('internship', 'Internship Break'),
        ('medical', 'Medical Break'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='breaks')
    break_type = models.CharField(max_length=20, choices=BREAK_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    impact_on_internship = models.TextField(blank=True)
    supporting_document = models.FileField(upload_to='break_documents/', blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_breaks')
    remarks = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.register_number} - {self.get_break_type_display()}"
    


# ============================================
# MENTOR ASSIGNMENT MODELS
# ============================================

class MentorAssignment(models.Model):
    ASSIGNMENT_LEVELS = (
        ('programme', 'Programme'),
        ('batch', 'Batch'),
        ('student', 'Student'),
        ('internship', 'Internship Specific'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='mentor_assignments')
    faculty_mentor = models.ForeignKey('authentication.UserProfile', on_delete=models.CASCADE, related_name='mentor_assignments')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    assignment_level = models.CharField(max_length=20, choices=ASSIGNMENT_LEVELS, default='student')
    related_semester = models.CharField(max_length=50, blank=True)
    internship_record = models.ForeignKey('InternshipRecord', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentor_assignments')
    reason_for_change = models.TextField(blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_mentors')
    is_active = models.BooleanField(default=True)
    remarks = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.register_number} → {self.faculty_mentor.user.email} ({self.effective_from})"
    
    class Meta:
        ordering = ['-effective_from']
    
    def save(self, *args, **kwargs):
        """Auto-deactivate if effective_to date has passed"""
        from django.utils import timezone
        
        # If effective_to is set and is in the past, auto set is_active=False
        if self.effective_to and self.effective_to < timezone.now().date():
            self.is_active = False
        
        super().save(*args, **kwargs)


class AssessmentComponent(models.Model):
    ASSESSMENT_TYPES = (
        ('intermediate', 'Intermediate Assessment'),
        ('report', 'Report Evaluation'),
        ('presentation', 'Presentation/Review'),
        ('mentor', 'Mentor Evaluation'),
        ('viva', 'Final Viva'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    default_max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_assessment_type_display()})"


class AssessmentMarks(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('locked', 'Locked'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    internship_record = models.ForeignKey('InternshipRecord', on_delete=models.CASCADE, related_name='assessment_marks')
    assessment_component = models.ForeignKey(AssessmentComponent, on_delete=models.CASCADE, related_name='assessment_marks')
    assessment_name = models.CharField(max_length=200, blank=True)
    maximum_marks = models.DecimalField(max_digits=5, decimal_places=2)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    assessment_date = models.DateField(null=True, blank=True)
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_marks')
    supporting_document = models.FileField(upload_to='assessment_documents/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    remarks = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='locked_marks')
    
    def __str__(self):
        return f"{self.internship_record.student.register_number} - {self.assessment_component.name} ({self.marks_awarded}/{self.maximum_marks})"
    
    class Meta:
        ordering = ['-created_on']


class AssessmentMarksHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_marks = models.ForeignKey(AssessmentMarks, on_delete=models.CASCADE, related_name='edit_history')
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessment_mark_edits')
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    edited_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-edited_on']

    def __str__(self):
        return f"{self.assessment_marks_id} edited on {self.edited_on}"


class ConsolidatedScore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='consolidated_scores')
    regular_internship_average = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    assessment_internship_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_consolidated_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    calculation_formula = models.CharField(max_length=100, default='simple_average')
    is_finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='finalized_scores')
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.register_number} - Final: {self.final_consolidated_score}"
    
    class Meta:
        ordering = ['-created_on']
        unique_together = ('student', 'calculation_formula')


# apps/core/models.py - ADD THESE MODELS AT THE END

class AssessmentConfiguration(models.Model):
    """Configurable assessment rules"""
    CALCULATION_CHOICES = (
        ('simple_average', 'Simple Average'),
        ('weighted_average', 'Weighted Average'),
        ('best_n', 'Best N Internships'),
        ('all_with_assessment', 'All Internships + Assessment'),
        ('separate_components', 'Separate Components'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='assessment_configs')
    regular_internship_count = models.IntegerField(default=8)
    assessment_internship_enabled = models.BooleanField(default=True)
    assessment_internship_duration_months = models.IntegerField(default=3)
    include_intermediate_marks = models.BooleanField(default=False)
    calculation_formula = models.CharField(max_length=50, default='simple_average', choices=CALCULATION_CHOICES)
    best_n_value = models.IntegerField(default=5, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.programme.name} Assessment Config"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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


class AuditLog(models.Model):
    """Audit log for user actions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
