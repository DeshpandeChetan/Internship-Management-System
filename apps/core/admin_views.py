from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from ..authentication.models import UserProfile
from .models import (
    Programme, Batch, Student, Organisation, 
    InternshipRecord, BreakRecord,
    # Add these new imports
    MentorAssignment, AssessmentComponent, AssessmentMarks, ConsolidatedScore
)
from .decorators import admin_required
from .forms import (
    UserForm, StudentForm, OrganisationForm, InternshipForm, 
    BreakForm, MentorAssignmentForm, AssessmentMarksForm,
    AssessmentComponentForm, ProgrammeForm, BatchForm, ProfileForm
)
from datetime import datetime
import json

# ============================================
# ADMIN DASHBOARD
# ============================================

@admin_required
def admin_dashboard(request):
    """Admin Dashboard with statistics"""
    context = {
        'total_users': UserProfile.objects.count(),
        'total_students': Student.objects.count(),
        'total_organisations': Organisation.objects.count(),
        'total_internships': InternshipRecord.objects.count(),
        'pending_verifications': InternshipRecord.objects.filter(verification_status='submitted').count(),
        'pending_marks': InternshipRecord.objects.filter(verification_status='verified', assessment_marks__isnull=True).count(),
        'pending_approvals': InternshipRecord.objects.filter(verification_status='verified', completion_status='pending').count(),
        'active_tab': 'admin_dashboard'
    }
    return render(request, 'admin/dashboard.html', context)


# ============================================
# USER MANAGEMENT
# ============================================

@admin_required
def user_list(request):
    """List all users with filtering"""
    users = UserProfile.objects.all().select_related('user')
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    context = {
        'users': users,
        'roles': UserProfile.ROLE_CHOICES,
        'active_tab': 'admin_users'
    }
    return render(request, 'admin/users.html', context)

@admin_required
def user_add(request):
    """Add new user with role"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'User {user.email} created successfully!')
                return redirect('admin_users')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserForm()
    
    return render(request, 'admin/user_form_modal.html', {'form': form})

@admin_required
def user_edit(request, pk):
    """Edit user details and role"""
    profile = get_object_or_404(UserProfile, pk=pk)
    user = profile.user
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'User {user.email} updated successfully!')
                return redirect('admin_users')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserForm(instance=user)
        form.fields['role'].initial = profile.role
        form.fields['phone_number'].initial = profile.phone_number
        form.fields['is_active'].initial = profile.is_active
    
    return render(request, 'admin/user_form_modal.html', {'form': form, 'edit': True})

@admin_required
def user_delete(request, pk):
    """Delete user (soft delete)"""
    profile = get_object_or_404(UserProfile, pk=pk)
    
    if request.method == 'POST':
        try:
            profile.is_active = False
            profile.save()
            messages.success(request, f'User {profile.user.email} deactivated successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
        return redirect('admin_users')
    
    return render(request, 'admin/user_confirm_delete.html', {'profile': profile})


# ============================================
# STUDENT MANAGEMENT
# ============================================

@admin_required
def student_list(request):
    """List all students with filtering"""
    students = Student.objects.all().select_related('programme', 'batch')
    
    # Filters
    programme = request.GET.get('programme')
    if programme:
        students = students.filter(programme_id=programme)
    
    batch = request.GET.get('batch')
    if batch:
        students = students.filter(batch_id=batch)
    
    status = request.GET.get('status')
    if status:
        students = students.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        students = students.filter(
            Q(name__icontains=search) |
            Q(register_number__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'students': students,
        'programmes': Programme.objects.filter(is_active=True),
        'batches': Batch.objects.filter(is_active=True),
        'status_choices': Student.STATUS_CHOICES,
        'active_tab': 'admin_students'
    }
    return render(request, 'admin/students.html', context)

from django.http import JsonResponse
from django.template.loader import render_to_string

def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                student = form.save(commit=False)
                student.created_by = request.user
                student.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                messages.success(request, f'Student {student.name} added successfully!')
                return redirect('admin_students')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'html': render_to_string('admin/student_form_ajax.html', {'form': form, 'edit': False})})
                messages.error(request, f'Error adding student: {str(e)}')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'html': render_to_string('admin/student_form_ajax.html', {'form': form, 'edit': False})})
    else:
        form = StudentForm()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'html': render_to_string('admin/student_form_ajax.html', {'form': form, 'edit': False})})
    
    return render(request, 'admin/student_form_modal.html', {'form': form})

@admin_required
def student_detail(request, pk):
    """View student details with all related information"""
    student = get_object_or_404(Student, pk=pk)
    internships = InternshipRecord.objects.filter(student=student)
    breaks = BreakRecord.objects.filter(student=student)
    mentor_assignments = MentorAssignment.objects.filter(student=student)
    
    context = {
        'student': student,
        'internships': internships,
        'breaks': breaks,
        'mentor_assignments': mentor_assignments,
        'active_tab': 'admin_students'
    }
    return render(request, 'admin/student_detail_modal.html', context)

@admin_required
def student_edit(request, pk):
    """Edit student details"""
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Student {student.name} updated successfully!')
                return redirect('admin_students')
            except Exception as e:
                messages.error(request, f'Error updating student: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'admin/student_form_modal.html', {'form': form, 'edit': True})

@admin_required
def student_delete(request, pk):
    """Delete student (soft delete)"""
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        try:
            student.status = 'discontinued'
            student.save()
            messages.success(request, f'Student {student.name} marked as discontinued!')
        except Exception as e:
            messages.error(request, f'Error deleting student: {str(e)}')
        return redirect('admin_students')
    
    return render(request, 'admin/student_confirm_delete.html', {'student': student})


# ============================================
# ORGANISATION MANAGEMENT
# ============================================

@admin_required
def organisation_list(request):
    """List all organisations with filtering"""
    organisations = Organisation.objects.all()
    
    org_type = request.GET.get('type')
    if org_type:
        organisations = organisations.filter(organisation_type=org_type)
    
    search = request.GET.get('search')
    if search:
        organisations = organisations.filter(
            Q(name__icontains=search) |
            Q(city__icontains=search) |
            Q(contact_person__icontains=search)
        )
    
    context = {
        'organisations': organisations,
        'types': Organisation.TYPE_CHOICES,
        'active_tab': 'admin_organisations'
    }
    return render(request, 'admin/organisations.html', context)

@admin_required
def organisation_add(request):
    """Add new organisation"""
    if request.method == 'POST':
        form = OrganisationForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Organisation added successfully!')
                return redirect('admin_organisations')
            except Exception as e:
                messages.error(request, f'Error adding organisation: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = OrganisationForm()
    
    return render(request, 'admin/organisation_form_modal.html', {'form': form})

@admin_required
def organisation_edit(request, pk):
    """Edit organisation details"""
    organisation = get_object_or_404(Organisation, pk=pk)
    
    if request.method == 'POST':
        form = OrganisationForm(request.POST, instance=organisation)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Organisation {organisation.name} updated successfully!')
                return redirect('admin_organisations')
            except Exception as e:
                messages.error(request, f'Error updating organisation: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = OrganisationForm(instance=organisation)
    
    return render(request, 'admin/organisation_form_modal.html', {'form': form, 'edit': True})

@admin_required
def organisation_delete(request, pk):
    """Delete organisation (soft delete)"""
    organisation = get_object_or_404(Organisation, pk=pk)
    
    if request.method == 'POST':
        try:
            organisation.is_active = False
            organisation.save()
            messages.success(request, f'Organisation {organisation.name} deactivated successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting organisation: {str(e)}')
        return redirect('admin_organisations')
    
    return render(request, 'admin/organisation_confirm_delete.html', {'organisation': organisation})


# ============================================
# INTERNSHIP MANAGEMENT
# ============================================

@admin_required
def internship_list(request):
    """List all internships with filtering"""
    internships = InternshipRecord.objects.all().select_related('student', 'organisation')
    
    # Filters
    internship_type = request.GET.get('type')
    if internship_type:
        internships = internships.filter(internship_type=internship_type)
    
    verification_status = request.GET.get('verification')
    if verification_status:
        internships = internships.filter(verification_status=verification_status)
    
    student = request.GET.get('student')
    if student:
        internships = internships.filter(student_id=student)
    
    context = {
        'internships': internships,
        'types': InternshipRecord.INTERNSHIP_TYPES,
        'verification_statuses': InternshipRecord.VERIFICATION_STATUS,
        'students': Student.objects.all(),
        'active_tab': 'admin_internships'
    }
    return render(request, 'admin/internships.html', context)

@admin_required
def internship_detail(request, pk):
    """View internship details with marks"""
    internship = get_object_or_404(InternshipRecord, pk=pk)
    marks = AssessmentMarks.objects.filter(internship_record=internship).select_related('assessment_component')
    
    context = {
        'internship': internship,
        'marks': marks,
        'active_tab': 'admin_internships'
    }
    return render(request, 'admin/internship_detail_modal.html', context)


# ============================================
# MENTOR ASSIGNMENT MANAGEMENT
# ============================================

@admin_required
def mentor_assignment_list(request):
    """List all mentor assignments"""
    assignments = MentorAssignment.objects.all().select_related('student', 'faculty_mentor')
    
    context = {
        'assignments': assignments,
        'active_tab': 'admin_mentor_assignments'
    }
    return render(request, 'admin/mentor_assignments.html', context)

@admin_required
def mentor_assignment_add(request):
    """Add new mentor assignment"""
    if request.method == 'POST':
        form = MentorAssignmentForm(request.POST)
        if form.is_valid():
            try:
                assignment = form.save(commit=False)
                assignment.assigned_by = request.user
                assignment.save()
                messages.success(request, 'Mentor assignment added successfully!')
                return redirect('admin_mentor_assignments')
            except Exception as e:
                messages.error(request, f'Error adding assignment: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MentorAssignmentForm()
    
    return render(request, 'admin/mentor_assignment_form_modal.html', {'form': form})


# ============================================
# BREAK MANAGEMENT
# ============================================

@admin_required
def break_list(request):
    """List all breaks"""
    breaks = BreakRecord.objects.all().select_related('student')
    
    context = {
        'breaks': breaks,
        'active_tab': 'admin_breaks'
    }
    return render(request, 'admin/breaks.html', context)

@admin_required
def break_add(request):
    """Add new break record"""
    if request.method == 'POST':
        form = BreakForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                break_record = form.save(commit=False)
                break_record.save()
                messages.success(request, 'Break record added successfully!')
                return redirect('admin_breaks')
            except Exception as e:
                messages.error(request, f'Error adding break: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = BreakForm()
    
    return render(request, 'admin/break_form_modal.html', {'form': form})


# ============================================
# ASSESSMENT CONFIGURATION
# ============================================

@admin_required
def assessment_config(request):
    """Configure assessment components"""
    components = AssessmentComponent.objects.all()
    
    if request.method == 'POST':
        form = AssessmentComponentForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Assessment component added successfully!')
                return redirect('admin_assessment_config')
            except Exception as e:
                messages.error(request, f'Error adding component: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AssessmentComponentForm()
    
    context = {
        'components': components,
        'form': form,
        'active_tab': 'admin_config'
    }
    return render(request, 'admin/assessment_config.html', context)

@admin_required
def assessment_component_delete(request, pk):
    """Delete assessment component"""
    component = get_object_or_404(AssessmentComponent, pk=pk)
    
    if request.method == 'POST':
        try:
            component.is_active = False
            component.save()
            messages.success(request, f'Component {component.name} deactivated successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting component: {str(e)}')
        return redirect('admin_assessment_config')
    
    return render(request, 'admin/component_confirm_delete.html', {'component': component})


# ============================================
# SYSTEM SETTINGS
# ============================================

@admin_required
def settings_view(request):
    """System settings"""
    programmes = Programme.objects.all()
    batches = Batch.objects.all()
    
    if request.method == 'POST':
        # Handle programme or batch creation
        if 'add_programme' in request.POST:
            form = ProgrammeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Programme added successfully!')
                return redirect('admin_settings')
        
        elif 'add_batch' in request.POST:
            form = BatchForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Batch added successfully!')
                return redirect('admin_settings')
    
    context = {
        'programmes': programmes,
        'batches': batches,
        'programme_form': ProgrammeForm(),
        'batch_form': BatchForm(),
        'active_tab': 'admin_settings'
    }
    return render(request, 'admin/settings.html', context)


# ============================================
# BULK OPERATIONS
# ============================================

@admin_required
def bulk_student_upload(request):
    """Bulk upload students via CSV"""
    if request.method == 'POST':
        # Handle CSV upload
        messages.success(request, 'Students uploaded successfully!')
        return redirect('admin_students')
    
    return render(request, 'admin/bulk_upload.html', {'active_tab': 'admin_students'})


# ============================================
# EXPORTS
# ============================================

@admin_required
def export_data(request, model_name):
    """Export data to Excel/CSV"""
    # Implementation for export
    return HttpResponse("Export functionality")

@admin_required
def user_toggle(request, pk):
    """Toggle user active status"""
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        profile.is_active = not profile.is_active
        profile.save()
        messages.success(request, f'User {profile.user.email} status updated successfully!')
        return redirect('admin_users')
    return redirect('admin_users')

@admin_required
def organisation_toggle(request, pk):
    """Toggle organisation active status"""
    organisation = get_object_or_404(Organisation, pk=pk)
    if request.method == 'POST':
        organisation.is_active = not organisation.is_active
        organisation.save()
        messages.success(request, f'Organisation {organisation.name} status updated successfully!')
        return redirect('admin_organisations')
    return redirect('admin_organisations')

@admin_required
def organisation_internships(request, pk):
    """View all internships for an organisation"""
    organisation = get_object_or_404(Organisation, pk=pk)
    internships = InternshipRecord.objects.filter(organisation=organisation).select_related('student')
    context = {
        'organisation': organisation,
        'internships': internships
    }
    return render(request, 'admin/organisation_internships_modal.html', context)

@admin_required
def student_internships(request, pk):
    """View all internships for a student"""
    student = get_object_or_404(Student, pk=pk)
    internships = InternshipRecord.objects.filter(student=student).select_related('organisation')
    context = {
        'student': student,
        'internships': internships
    }
    return render(request, 'admin/student_internships_modal.html', context)

@admin_required
def internship_marks(request, pk):
    """View marks for an internship"""
    internship = get_object_or_404(InternshipRecord, pk=pk)
    from ..models import AssessmentMarks
    marks = AssessmentMarks.objects.filter(internship_record=internship).select_related('assessment_component')
    context = {
        'internship': internship,
        'marks': marks
    }
    return render(request, 'admin/internship_marks_modal.html', context)

@admin_required
def mentor_assignment_edit(request, pk):
    """Edit mentor assignment"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    if request.method == 'POST':
        form = MentorAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mentor assignment updated successfully!')
            return redirect('admin_mentor_assignments')
    else:
        form = MentorAssignmentForm(instance=assignment)
    return render(request, 'admin/mentor_assignment_form_ajax.html', {'form': form, 'edit': True})

@admin_required
def mentor_assignment_detail(request, pk):
    """View mentor assignment details"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    return render(request, 'admin/mentor_assignment_detail_modal.html', {'assignment': assignment})

@admin_required
def mentor_assignment_delete(request, pk):
    """Delete mentor assignment"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Mentor assignment deleted successfully!')
        return redirect('admin_mentor_assignments')
    return redirect('admin_mentor_assignments')

@admin_required
def break_edit(request, pk):
    """Edit break record"""
    break_record = get_object_or_404(BreakRecord, pk=pk)
    if request.method == 'POST':
        form = BreakForm(request.POST, request.FILES, instance=break_record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Break record updated successfully!')
            return redirect('admin_breaks')
    else:
        form = BreakForm(instance=break_record)
    return render(request, 'admin/break_form_ajax.html', {'form': form, 'edit': True})

@admin_required
def break_detail(request, pk):
    """View break record details"""
    break_record = get_object_or_404(BreakRecord, pk=pk)
    return render(request, 'admin/break_detail_modal.html', {'break_record': break_record})

@admin_required
def break_delete(request, pk):
    """Delete break record"""
    break_record = get_object_or_404(BreakRecord, pk=pk)
    if request.method == 'POST':
        break_record.delete()
        messages.success(request, 'Break record deleted successfully!')
        return redirect('admin_breaks')
    return redirect('admin_breaks')

@admin_required
def admin_reports(request):
    """Admin Reports page"""
    return render(request, 'admin/reports.html', {'active_tab': 'admin_reports'})

@admin_required
def consolidated_report(request):
    """Consolidated marks report"""
    return render(request, 'admin/consolidated_report.html', {'active_tab': 'consolidated'})