# apps/core/forms.py

from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from .models import (
    Department, Programme, Batch, Student, Organisation, 
    InternshipRecord, BreakRecord,
    MentorAssignment, AssessmentMarks, AssessmentComponent
)
from ..authentication.models import UserProfile


# ============================================
# USER MANAGEMENT FORMS
# ============================================

ALLOWED_DOCUMENT_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx')
ADMIN_MANAGED_ROLE_CHOICES = tuple(
    choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'student'
)


def validate_document_file(uploaded_file):
    if not uploaded_file:
        return
    name = uploaded_file.name.lower()
    if not name.endswith(ALLOWED_DOCUMENT_EXTENSIONS):
        raise forms.ValidationError("Only PDF, JPG, PNG, DOC, and DOCX files are allowed.")

class UserForm(forms.ModelForm):
    """Form for creating/editing users"""
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=ADMIN_MANAGED_ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
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
                self.fields['department'].initial = self.instance.profile.department
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
                    'department': self.cleaned_data.get('department'),
                    'phone_number': self.cleaned_data.get('phone_number', ''),
                    'is_active': self.cleaned_data.get('is_active', True)
                }
            )
            if not created:
                profile.role = self.cleaned_data['role']
                profile.department = self.cleaned_data.get('department')
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
            'department', 'programme', 'batch', 'degree_start_date', 
            'degree_end_date', 'status', 'remarks'
        ]
        widgets = {
            'register_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
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
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['programme'].required = False
        self.fields['batch'].required = False
        self.fields['degree_start_date'].required = False
    
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
                    'department': student.department,
                    'phone_number': student.mobile or '',
                    'is_active': True,
                    'is_approved': True
                }
            )
            if not created:
                profile.role = 'student'
                profile.department = student.department
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
            'name', 'organisation_type', 'organisation_type_other', 'contact_person', 'designation',
            'email', 'phone', 'address', 'city', 'state', 'website',
            'area_of_work', 'feedback_rating', 'is_active', 'remarks'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'organisation_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_organisation_type'}),
            'organisation_type_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify organisation type'}),
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

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Organisation.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An organisation with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        organisation_type = cleaned_data.get('organisation_type')
        other_type = cleaned_data.get('organisation_type_other')
        if organisation_type == 'other' and not other_type:
            self.add_error('organisation_type_other', "Please specify the organisation type.")
        if organisation_type != 'other':
            cleaned_data['organisation_type_other'] = ''
        return cleaned_data


# ============================================
# INTERNSHIP MANAGEMENT FORMS
# ============================================

class InternshipForm(forms.ModelForm):
    """Form for creating/editing internships"""
    class Meta:
        model = InternshipRecord
        fields = [
            'organisation', 'internship_type', 'internship_number',
            'academic_phase', 'related_semester', 'start_date', 'end_date', 'mode',
            'nature_of_work', 'supporting_document', 'certificate_upload', 'report_upload',
            'date_override_approved', 'date_override_reason', 'submission_date', 'completion_status',
            'verification_status', 'remarks'
        ]
        widgets = {
            'organisation': forms.Select(attrs={'class': 'form-control'}),
            'internship_type': forms.Select(attrs={'class': 'form-control'}),
            'internship_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1-8 or Assessment'}),
            'academic_phase': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Year 1, Year 2, etc.'}),
            'related_semester': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'nature_of_work': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
            'certificate_upload': forms.FileInput(attrs={'class': 'form-control'}),
            'report_upload': forms.FileInput(attrs={'class': 'form-control'}),
            'date_override_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date_override_reason': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'submission_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_status': forms.Select(attrs={'class': 'form-control'}),
            'verification_status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        self.fields['organisation'].queryset = Organisation.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        internship_type = cleaned_data.get('internship_type')
        internship_number = cleaned_data.get('internship_number')
        date_override_approved = cleaned_data.get('date_override_approved')
        date_override_reason = cleaned_data.get('date_override_reason')
        student = self.student or getattr(self.instance, 'student', None)
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")

        validate_document_file(cleaned_data.get('supporting_document'))
        validate_document_file(cleaned_data.get('certificate_upload'))
        validate_document_file(cleaned_data.get('report_upload'))

        if date_override_approved and not date_override_reason:
            self.add_error('date_override_reason', "Please mention the approved override reason.")

        if student and start_date and end_date and not date_override_approved:
            if student.degree_start_date and start_date < student.degree_start_date:
                self.add_error('start_date', "Internship start date must fall within the student's degree period unless override is approved.")
            if student.degree_end_date and end_date > student.degree_end_date:
                self.add_error('end_date', "Internship end date must fall within the student's degree period unless override is approved.")

        if student and internship_type == 'regular':
            try:
                number = int(str(internship_number).strip())
            except (TypeError, ValueError):
                self.add_error('internship_number', "Regular internship number must be between 1 and 8.")
            else:
                if number < 1 or number > 8:
                    self.add_error('internship_number', "Regular internship number must be between 1 and 8.")
                cleaned_data['internship_number'] = str(number)
                duplicate = InternshipRecord.objects.filter(
                    student=student,
                    internship_type='regular',
                    internship_number=str(number)
                ).exclude(pk=self.instance.pk)
                if duplicate.exists():
                    self.add_error('internship_number', "This regular internship number already exists for the student.")

            regular_count = InternshipRecord.objects.filter(
                student=student,
                internship_type='regular'
            ).exclude(pk=self.instance.pk).count()
            if regular_count >= 8:
                self.add_error('internship_type', "Only eight regular internships are supported per student. Use Additional or Repeated if required.")

        if student and internship_type == 'assessment':
            duplicate = InternshipRecord.objects.filter(
                student=student,
                internship_type='assessment'
            ).exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error('internship_type', "Only one final assessment internship is supported per student.")
            if start_date and end_date:
                duration_days = (end_date - start_date).days + 1
                if duration_days < 80 or duration_days > 100:
                    self.add_error('end_date', "Assessment internship should be approximately three months.")
            if start_date and student.degree_start_date and not date_override_approved:
                try:
                    fifth_year_start = student.degree_start_date.replace(year=student.degree_start_date.year + 4)
                except ValueError:
                    fifth_year_start = student.degree_start_date.replace(month=2, day=28, year=student.degree_start_date.year + 4)
                if start_date < fifth_year_start:
                    self.add_error('start_date', "Assessment internship must be in the fifth academic year unless override is approved.")
        
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
            'impact_on_internship', 'supporting_document', 'approved_by', 'remarks'
        ]
        widgets = {
            'break_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'impact_on_internship': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
            'approved_by': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        student = cleaned_data.get('student') or getattr(self.instance, 'student', None)
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")

        validate_document_file(cleaned_data.get('supporting_document'))

        if student and start_date and end_date:
            degree_end = student.degree_end_date
            if student.degree_start_date and start_date < student.degree_start_date:
                self.add_error('start_date', "Break start date must be within the student's degree period.")
            if degree_end and end_date > degree_end:
                self.add_error('end_date', "Break end date must be within the student's degree period.")

        validate_document_file(cleaned_data.get('supporting_document'))
        
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

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        effective_from = cleaned_data.get('effective_from')
        effective_to = cleaned_data.get('effective_to')

        if effective_from and effective_to and effective_to < effective_from:
            self.add_error('effective_to', "Effective to date cannot be before effective from date.")

        if student and effective_from:
            active_overlap = MentorAssignment.objects.filter(
                student=student,
                is_active=True,
            ).exclude(pk=self.instance.pk)

            if effective_to:
                active_overlap = active_overlap.filter(
                    Q(effective_to__isnull=True) | Q(effective_to__gte=effective_from),
                    effective_from__lte=effective_to,
                )
            else:
                active_overlap = active_overlap.filter(
                    Q(effective_to__isnull=True) | Q(effective_to__gte=effective_from)
                )

            if active_overlap.exists():
                self.add_error('student', "This student already has an active mentor assignment for the selected period.")

        return cleaned_data


# ============================================
# ASSESSMENT MARKS FORMS
# ============================================

class AssessmentMarksForm(forms.ModelForm):
    """Form for entering assessment marks"""
    class Meta:
        model = AssessmentMarks
        fields = [
            'internship_record', 'assessment_component', 'assessment_name', 'maximum_marks',
            'marks_awarded', 'weightage', 'assessment_date', 'supporting_document', 'remarks', 'status'
        ]
        widgets = {
            'internship_record': forms.Select(attrs={'class': 'form-control'}),
            'assessment_component': forms.Select(attrs={'class': 'form-control'}),
            'assessment_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review 1, Mid Review, Final Viva'}),
            'maximum_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'marks_awarded': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'weightage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'assessment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        assessment_component = cleaned_data.get('assessment_component')
        marks_awarded = cleaned_data.get('marks_awarded')
        maximum_marks = cleaned_data.get('maximum_marks')
        status = cleaned_data.get('status')

        if self.instance and self.instance.pk and self.instance.status == 'locked':
            raise forms.ValidationError("Locked marks cannot be edited.")
        
        if marks_awarded and maximum_marks:
            if marks_awarded > maximum_marks:
                raise forms.ValidationError("Marks awarded cannot exceed maximum marks.")
            if marks_awarded < 0:
                raise forms.ValidationError("Marks awarded cannot be negative.")

        if assessment_component and assessment_component.assessment_type == 'viva' and maximum_marks != 100:
            self.add_error('maximum_marks', "Final viva marks must be out of 100.")

        if status == 'locked':
            approved_instance = self.instance and self.instance.pk and self.instance.status == 'approved'
            if not approved_instance:
                self.add_error('status', "Marks can be locked only after approval.")

        validate_document_file(cleaned_data.get('supporting_document'))
        
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


class DepartmentForm(forms.ModelForm):
    """Form for creating/editing departments"""
    class Meta:
        model = Department
        fields = ['name', 'code', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Department.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A department with this name already exists.")
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if Department.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A department with this code already exists.")
        return code


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
