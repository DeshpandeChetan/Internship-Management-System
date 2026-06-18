import uuid
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'System Admin'),
        ('dept_admin', 'Department Admin'),
        ('faculty_mentor', 'Faculty Mentor'),
        ('evaluator', 'Faculty Evaluator'),
        ('hod', 'HoD/Coordinator'),
        ('student', 'Student'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"
    
    def get_full_name(self):
        return self.user.get_full_name() or self.user.email
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_dept_admin(self):
        return self.role == 'dept_admin'
    
    def is_mentor(self):
        return self.role == 'faculty_mentor'
    
    def is_evaluator(self):
        return self.role == 'evaluator'
    
    def is_hod(self):
        return self.role == 'hod'
    
    def is_student(self):
        return self.role == 'student'
    
    class Meta:
        ordering = ['-created_on']