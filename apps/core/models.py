#Internship-Management-System\apps\core\models.py
import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.authentication.models import UserProfile

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
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='students')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='students')
    
    # Degree dates
    degree_start_date = models.DateField()
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
        return f"{self.name} ({self.get_organisation_type_display()})"

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
    nature_of_work = models.TextField(blank=True)
    submission_date = models.DateField(null=True, blank=True)
    completion_status = models.CharField(max_length=20, choices=COMPLETION_STATUS, default='pending')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='draft')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_internships')
    verified_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_internships')
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    @property
    def duration(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None
    
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
    maximum_marks = models.DecimalField(max_digits=5, decimal_places=2)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    assessment_date = models.DateField(null=True, blank=True)
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_marks')
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
        unique_together = ('internship_record', 'assessment_component')


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