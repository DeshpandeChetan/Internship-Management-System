# Internship-Management-System\apps\forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    User, Student, Organisation, InternshipRecord, BreakRecord, 
    MentorAssignment, AssessmentMarks, Document, Programme, Batch,
    AssessmentConfiguration
)
from django.core.exceptions import ValidationError
from django.utils import timezone


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2', 'role', 'first_name', 'last_name')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.role = self.cleaned_data.get('role', user.role)
        if commit:
            user.save()
        return user


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    register_number = forms.CharField(max_length=50)
    name = forms.CharField(max_length=200)
    mobile = forms.CharField(max_length=15, required=False)
    programme = forms.ModelChoiceField(queryset=Programme.objects.filter(is_active=True), required=True)
    batch = forms.ModelChoiceField(queryset=Batch.objects.filter(is_active=True), required=True)
    degree_start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    degree_end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model = User
        fields = (
            'username', 'email', 'phone', 'password1', 'password2',
            'first_name', 'last_name', 'register_number', 'name',
            'mobile', 'programme', 'batch', 'degree_start_date', 'degree_end_date'
        )

    def clean(self):
        cleaned_data = super().clean()
        degree_start = cleaned_data.get('degree_start_date')
        degree_end = cleaned_data.get('degree_end_date')

        if degree_start and degree_end and degree_end <= degree_start:
            raise ValidationError('Degree end date must be after start date')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.role = 'student'
        if commit:
            user.save()

        student = Student(
            register_number=self.cleaned_data['register_number'],
            name=self.cleaned_data['name'],
            email=self.cleaned_data['email'],
            mobile=self.cleaned_data.get('mobile', ''),
            programme=self.cleaned_data['programme'],
            batch=self.cleaned_data['batch'],
            degree_start_date=self.cleaned_data['degree_start_date'],
            degree_end_date=self.cleaned_data['degree_end_date'],
            user=user,
        )
        student.save()
        return user


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        exclude = ('created_at', 'updated_at')
        widgets = {
            'degree_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'degree_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'register_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'programme': forms.Select(attrs={'class': 'form-control'}),
            'batch': forms.Select(attrs={'class': 'form-control'}),
            'current_status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        degree_start = cleaned_data.get('degree_start_date')
        degree_end = cleaned_data.get('degree_end_date')
        
        if degree_start and degree_end and degree_end <= degree_start:
            raise ValidationError('Degree end date must be after start date')
        
        return cleaned_data


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = '__all__'
        exclude = ('created_at', 'updated_at', 'student_count')
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
            'area_of_work': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'feedback_rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        city = cleaned_data.get('city')
        state = cleaned_data.get('state')

        duplicates = Organisation.objects.filter(
            name__iexact=name.strip() if name else '',
            email__iexact=email.strip() if email else ''
        )
        if self.instance and self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise ValidationError('An organisation with the same name and email already exists.')

        if name and phone and city and state:
            duplicates = Organisation.objects.filter(
                name__iexact=name.strip(),
                phone__iexact=phone.strip(),
                city__iexact=city.strip(),
                state__iexact=state.strip(),
            )
            if self.instance and self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)

            if duplicates.exists():
                raise ValidationError('An organisation with the same name, phone, and location already exists.')

        return cleaned_data


class InternshipRecordForm(forms.ModelForm):
    class Meta:
        model = InternshipRecord
        fields = '__all__'
        exclude = ('created_at', 'updated_at', 'duration_days', 'verified_by', 'verified_at')
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'organisation': forms.Select(attrs={'class': 'form-control'}),
            'internship_type': forms.Select(attrs={'class': 'form-control'}),
            'internship_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 9}),
            'related_semester': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'nature_of_work': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'completion_status': forms.Select(attrs={'class': 'form-control'}),
            'verification_status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        internship_type = cleaned_data.get('internship_type')
        internship_number = cleaned_data.get('internship_number')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError('End date must be after start date')
        
        if student and start_date:
            if start_date < student.degree_start_date or (end_date and end_date > student.degree_end_date):
                raise ValidationError('Internship dates must fall within student\'s degree period')
        
        if internship_type == 'regular' and internship_number:
            if internship_number < 1 or internship_number > 8:
                raise ValidationError('Regular internship number must be between 1 and 8')
        
        return cleaned_data


class BreakRecordForm(forms.ModelForm):
    class Meta:
        model = BreakRecord
        fields = '__all__'
        exclude = ('created_at', 'updated_at')
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'break_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'approved_by': forms.TextInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
            'impact_on_internship': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError('End date must be after start date')
        
        if student and start_date:
            if start_date < student.degree_start_date or end_date > student.degree_end_date:
                raise ValidationError('Break dates must fall within student\'s degree period')

            overlapping = BreakRecord.objects.filter(student=student).exclude(id=self.instance.id if self.instance else None).filter(
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if overlapping.exists():
                raise ValidationError('This break overlaps with an existing break record for the student.')
        
        return cleaned_data


class MentorAssignmentForm(forms.ModelForm):
    class Meta:
        model = MentorAssignment
        fields = '__all__'
        exclude = ('created_at', 'updated_at', 'assigned_by')
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
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        effective_from = cleaned_data.get('effective_from')
        effective_to = cleaned_data.get('effective_to')
        
        if effective_from and effective_to and effective_to <= effective_from:
            raise ValidationError('Effective to date must be after effective from date')
        
        # Check for overlapping assignments
        if student and effective_from:
            overlapping = MentorAssignment.objects.filter(
                student=student,
                effective_to__isnull=True
            ).exclude(id=self.instance.id if self.instance else None)
            
            if overlapping.exists():
                raise ValidationError('Student already has an active mentor assignment')
        
        return cleaned_data


class AssessmentMarksForm(forms.ModelForm):
    class Meta:
        model = AssessmentMarks
        fields = '__all__'
        exclude = ('created_at', 'updated_at')
        widgets = {
            'internship_record': forms.Select(attrs={'class': 'form-control'}),
            'assessment_type': forms.Select(attrs={'class': 'form-control'}),
            'assessment_name': forms.TextInput(attrs={'class': 'form-control'}),
            'maximum_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'marks_awarded': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'weightage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'assessment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'evaluator': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        marks_awarded = cleaned_data.get('marks_awarded')
        maximum_marks = cleaned_data.get('maximum_marks')
        
        if marks_awarded and maximum_marks:
            if marks_awarded > maximum_marks:
                raise ValidationError(f'Marks awarded cannot exceed {maximum_marks}')
            if marks_awarded < 0:
                raise ValidationError('Marks awarded cannot be negative')
        
        return cleaned_data


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ('document_type', 'file', 'remarks')
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = '__all__'
        exclude = ('created_at',)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = '__all__'
        exclude = ('created_at',)
        widgets = {
            'programme': forms.Select(attrs={'class': 'form-control'}),
            'batch_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2020-2025'}),
            'academic_year_start': forms.NumberInput(attrs={'class': 'form-control'}),
            'academic_year_end': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AssessmentConfigurationForm(forms.ModelForm):
    class Meta:
        model = AssessmentConfiguration
        fields = '__all__'
        exclude = ('created_at', 'updated_at')
        widgets = {
            'programme': forms.Select(attrs={'class': 'form-control'}),
            'regular_internship_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'assessment_internship_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assessment_internship_duration_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'include_intermediate_marks': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'calculation_formula': forms.Select(attrs={'class': 'form-control'}),
            'best_n_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BulkStudentUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel/CSV File',
        help_text='Upload Excel or CSV file with columns: register_number, name, email, programme_code, batch_year, degree_start_date, degree_end_date'
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            raise ValidationError('Please upload an Excel or CSV file (.xlsx, .xls, or .csv)')
        return file


class BulkOrganisationUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel/CSV File',
        help_text='Upload Excel or CSV file with columns: name, organisation_type, contact_person, email, phone, city'
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            raise ValidationError('Please upload an Excel or CSV file (.xlsx, .xls, or .csv)')
        return file