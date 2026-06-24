#Internship-Management-System\apps\authentication\models.py
import uuid
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'System Admin'),
        ('faculty_mentor', 'Faculty Mentor'),
        ('evaluator', 'Faculty Evaluator'),
        ('hod', 'HoD/Coordinator'),
        ('student', 'Student'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.ForeignKey('core.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)  # User is active
    is_approved = models.BooleanField(default=False)  # Admin approval required for students
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"
    
    def get_full_name(self):
        return self.user.get_full_name() or self.user.email
    
    def can_login(self):
        """Check if user can login (active and approved)"""
        if self.role in ['admin', 'faculty_mentor', 'evaluator', 'hod']:
            return self.is_active
        return self.is_active and self.is_approved
