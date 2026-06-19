# apps/core/forms.py

from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import (
    Programme, Batch, Student, Organisation, 
    InternshipRecord, BreakRecord,
    MentorAssignment, AssessmentMarks, AssessmentComponent
)
from ..authentication.models import UserProfile


# ============================================
# USER MANAGEMENT FORMS
# ============================================

class UserForm(forms.ModelForm):
    """Form for creating/editing users"""
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        required=False, 
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if hasattr(self.instance, 'profile'):
                self.fields['role'].initial = self.instance.profile.role
                self.fields['phone_number'].initial = self.instance.profile.phone_number
                self.fields['is_active'].initial = self.instance.profile.is_active
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.set_password('temp123')
        
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': self.cleaned_data['role'],
                    'phone_number': self.cleaned_data.get('phone_number', ''),
                    'is_active': self.cleaned_data.get('is_active', True)
                }
            )
            if not created:
                profile.role = self.cleaned_data['role']
                profile.phone_number = self.cleaned_data.get('phone_number', '')
                profile.is_active = self.cleaned_data.get('is_active', True)
                profile.save()
        return user


# ============================================
# STUDENT MANAGEMENT FORMS - COMPLETELY FIXED
# ============================================

# apps/core/forms.py (StudentForm only)

# apps/core/forms.py (StudentForm only - FIXED)

class StudentForm(forms.ModelForm):
    """Form for creating/editing students - No password needed for Google Login"""
    
    class Meta:
        model = Student
        fields = [
            'register_number', 'name', 'email', 'mobile', 
            'programme', 'batch', 'degree_start_date', 
            'degree_end_date', 'status', 'remarks'
        ]
        widgets = {
            'register_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'programme': forms.Select(attrs={'class': 'form-control'}),
            'batch': forms.Select(attrs={'class': 'form-control'}),
            'degree_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'degree_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['programme'].queryset = Programme.objects.filter(is_active=True)
        self.fields['batch'].queryset = Batch.objects.filter(is_active=True)
    
    def clean_register_number(self):
        register_number = self.cleaned_data.get('register_number')
        if Student.objects.filter(register_number=register_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A student with this register number already exists.")
        return register_number
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Student.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A student with this email already exists.")
        return email
    
    def save(self, commit=True):
        """Simple save - creates User without password (Google Login)"""
        student = super().save(commit=False)
        
        # Create user for Google Login (no password needed)
        if not student.user:
            user, created = User.objects.get_or_create(
                email=student.email,
                defaults={
                    'username': student.email,
                    'first_name': student.name.split()[0] if ' ' in student.name else student.name,
                    'last_name': ' '.join(student.name.split()[1:]) if ' ' in student.name else '',
                }
            )
            # No password set - Google Login will handle authentication
            if created:
                user.save()
            student.user = user
        
        # Create UserProfile for role-based access
        if student.user:
            profile, created = UserProfile.objects.get_or_create(
                user=student.user,
                defaults={
                    'role': 'student',
                    'phone_number': student.mobile or '',
                    'is_active': True,
                    'is_approved': True
                }
            )
            if not created:
                profile.role = 'student'
                profile.phone_number = student.mobile or ''
                profile.is_approved = True
                profile.save()
        
        if commit:
            student.save()
        
        return student


# ============================================
# ORGANISATION MANAGEMENT FORMS
# ============================================

class OrganisationForm(forms.ModelForm):
    """Form for creating/editing organisations"""
    class Meta:
        model = Organisation
        fields = [
            'name', 'organisation_type', 'contact_person', 'designation',
            'email', 'phone', 'address', 'city', 'state', 'website',
            'area_of_work', 'feedback_rating', 'is_active', 'remarks'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'organisation_type': forms.Select(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'area_of_work': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'feedback_rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '5'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Organisation.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An organisation with this name already exists.")
        return name


# ============================================
# INTERNSHIP MANAGEMENT FORMS
# ============================================

class InternshipForm(forms.ModelForm):
    """Form for creating/editing internships"""
    class Meta:
        model = InternshipRecord
        fields = [
            'organisation', 'internship_type', 'internship_number',
            'related_semester', 'start_date', 'end_date', 'mode',
            'nature_of_work', 'submission_date', 'completion_status',
            'verification_status', 'remarks'
        ]
        widgets = {
            'organisation': forms.Select(attrs={'class': 'form-control'}),
            'internship_type': forms.Select(attrs={'class': 'form-control'}),
            'internship_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1-8 or Assessment'}),
            'related_semester': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'nature_of_work': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'submission_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_status': forms.Select(attrs={'class': 'form-control'}),
            'verification_status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organisation'].queryset = Organisation.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data


# ============================================
# BREAK MANAGEMENT FORMS
# ============================================

class BreakForm(forms.ModelForm):
    """Form for creating/editing breaks"""
    class Meta:
        model = BreakRecord
        fields = [
            'break_type', 'start_date', 'end_date', 'reason',
            'impact_on_internship', 'supporting_document', 'remarks'
        ]
        widgets = {
            'break_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'impact_on_internship': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data


# ============================================
# MENTOR ASSIGNMENT FORMS
# ============================================

class MentorAssignmentForm(forms.ModelForm):
    """Form for creating/editing mentor assignments"""
    class Meta:
        model = MentorAssignment
        fields = [
            'student', 'faculty_mentor', 'effective_from', 'effective_to',
            'assignment_level', 'related_semester', 'internship_record',
            'reason_for_change', 'remarks'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'faculty_mentor': forms.Select(attrs={'class': 'form-control'}),
            'effective_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'effective_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'assignment_level': forms.Select(attrs={'class': 'form-control'}),
            'related_semester': forms.TextInput(attrs={'class': 'form-control'}),
            'internship_record': forms.Select(attrs={'class': 'form-control'}),
            'reason_for_change': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['faculty_mentor'].queryset = UserProfile.objects.filter(
            role__in=['faculty_mentor', 'hod']
        )


# ============================================
# ASSESSMENT MARKS FORMS
# ============================================

class AssessmentMarksForm(forms.ModelForm):
    """Form for entering assessment marks"""
    class Meta:
        model = AssessmentMarks
        fields = [
            'internship_record', 'assessment_component', 'maximum_marks',
            'marks_awarded', 'weightage', 'assessment_date', 'remarks', 'status'
        ]
        widgets = {
            'internship_record': forms.Select(attrs={'class': 'form-control'}),
            'assessment_component': forms.Select(attrs={'class': 'form-control'}),
            'maximum_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'marks_awarded': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'weightage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'assessment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        marks_awarded = cleaned_data.get('marks_awarded')
        maximum_marks = cleaned_data.get('maximum_marks')
        
        if marks_awarded and maximum_marks:
            if marks_awarded > maximum_marks:
                raise forms.ValidationError("Marks awarded cannot exceed maximum marks.")
            if marks_awarded < 0:
                raise forms.ValidationError("Marks awarded cannot be negative.")
        
        return cleaned_data


# ============================================
# ASSESSMENT COMPONENT FORMS
# ============================================

class AssessmentComponentForm(forms.ModelForm):
    """Form for creating/editing assessment components"""
    class Meta:
        model = AssessmentComponent
        fields = ['name', 'assessment_type', 'default_max_marks', 'weightage', 'is_mandatory', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'assessment_type': forms.Select(attrs={'class': 'form-control'}),
            'default_max_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'weightage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ============================================
# PROFILE FORMS
# ============================================

class ProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            if commit:
                self.user.save()
                profile.save()
        return profile


# ============================================
# PROGRAMME AND BATCH FORMS
# ============================================

class ProgrammeForm(forms.ModelForm):
    """Form for creating/editing programmes"""
    class Meta:
        model = Programme
        fields = ['name', 'code', 'duration_years', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BatchForm(forms.ModelForm):
    """Form for creating/editing batches"""
    class Meta:
        model = Batch
        fields = ['name', 'programme', 'start_year', 'end_year', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'programme': forms.Select(attrs={'class': 'form-control'}),
            'start_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'end_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }