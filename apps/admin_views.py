# Internship-Management-System\apps\admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Avg, Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import F
import pandas as pd
import json

from .models import (
    User, Student, Organisation, InternshipRecord, BreakRecord,
    MentorAssignment, AssessmentMarks, Programme, Batch,
    AssessmentConfiguration, AuditLog, Notification
)
from .forms import (
    UserRegistrationForm, StudentForm, OrganisationForm, ProgrammeForm, BatchForm,
    AssessmentConfigurationForm, BulkStudentUploadForm, BulkOrganisationUploadForm
)
from .utils.permissions import is_admin, is_dept_admin
from .utils.calculations import calculate_student_consolidated_marks
from .utils.report_generator import generate_excel_report, generate_pdf_report


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard with statistics"""
    context = {
        'active_tab': 'admin_dashboard',
        'total_students': Student.objects.count(),
        'active_students': Student.objects.filter(current_status='active').count(),
        'total_organisations': Organisation.objects.filter(status='active').count(),
        'total_internships': InternshipRecord.objects.count(),
        'completed_internships': InternshipRecord.objects.filter(completion_status='completed').count(),
        'pending_verifications': InternshipRecord.objects.filter(verification_status='submitted').count(),
        'pending_marks': AssessmentMarks.objects.filter(status='submitted').count(),
        'recent_students': Student.objects.all().order_by('-created_at')[:10],
        'recent_internships': InternshipRecord.objects.all().order_by('-created_at')[:10],
        'internship_by_status': InternshipRecord.objects.values('verification_status').annotate(count=Count('id')),
        'internship_by_type': InternshipRecord.objects.values('internship_type').annotate(count=Count('id')),
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def student_management(request):
    """Manage students - list, add, edit, delete"""
    students = Student.objects.select_related('programme', 'batch', 'user').all()
    
    # Filters
    programme = request.GET.get('programme')
    batch = request.GET.get('batch')
    status = request.GET.get('status')
    search = request.GET.get('search')
    degree_start = request.GET.get('degree_start')
    degree_end = request.GET.get('degree_end')
    
    if programme:
        students = students.filter(programme_id=programme)
    if batch:
        students = students.filter(batch_id=batch)
    if status:
        students = students.filter(current_status=status)
    if search:
        students = students.filter(
            Q(register_number__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )
    if degree_start:
        students = students.filter(degree_start_date__gte=degree_start)
    if degree_end:
        students = students.filter(degree_end_date__lte=degree_end)
    
    students = students.order_by('register_number')
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'admin_students',
        'students': page_obj,
        'programmes': Programme.objects.filter(is_active=True),
        'batches': Batch.objects.filter(is_active=True),
        'status_choices': Student.STATUS_CHOICES,
        'total_count': students.count(),
        'filter_values': {
            'programme': programme,
            'batch': batch,
            'status': status,
            'search': search,
            'degree_start': degree_start,
            'degree_end': degree_end,
        },
    }
    return render(request, 'admin/students.html', context)


@login_required
@user_passes_test(is_admin)
def add_student(request):
    """Add new student"""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'Student {student.name} added successfully!')
            return redirect('admin_students')
    else:
        form = StudentForm()
    
    context = {
        'active_tab': 'admin_students',
        'form': form,
        'title': 'Add Student',
    }
    return render(request, 'admin/student_form.html', context)


@login_required
@user_passes_test(is_admin)
def edit_student(request, student_id):
    """Edit student details"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student {student.name} updated successfully!')
            return redirect('admin_students')
    else:
        form = StudentForm(instance=student)
    
    context = {
        'active_tab': 'admin_students',
        'form': form,
        'student': student,
        'title': 'Edit Student',
    }
    return render(request, 'admin/student_form.html', context)


@login_required
@user_passes_test(is_admin)
def delete_student(request, student_id):
    """Delete student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f'Student {student_name} deleted successfully!')
        return redirect('admin_students')
    
    context = {
        'student': student,
        'title': 'Delete Student',
    }
    return render(request, 'admin/student_confirm_delete.html', context)


@login_required
@user_passes_test(is_admin)
def bulk_upload_students(request):
    """Bulk upload students via Excel/CSV"""
    if request.method == 'POST':
        form = BulkStudentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                if excel_file.name.endswith('.csv'):
                    df = pd.read_csv(excel_file)
                else:
                    df = pd.read_excel(excel_file)

                success_count = 0
                error_count = 0

                for index, row in df.iterrows():
                    try:
                        programme = Programme.objects.get(code=str(row['programme_code']).strip())
                        batch = Batch.objects.get(batch_year=str(row['batch_year']).strip(), programme=programme)
                        
                        student = Student(
                            register_number=str(row['register_number']).strip(),
                            name=row['name'],
                            email=row['email'],
                            programme=programme,
                            batch=batch,
                            degree_start_date=pd.to_datetime(row['degree_start_date']).date(),
                            degree_end_date=pd.to_datetime(row['degree_end_date']).date(),
                            mobile=str(row.get('mobile', '')).strip() if 'mobile' in row else '',
                        )
                        student.save()
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error at row {index}: {e}")

                messages.success(request, f'Successfully uploaded {success_count} students. Errors: {error_count}')
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
            
            return redirect('admin_students')
    else:
        form = BulkStudentUploadForm()
    
    context = {
        'active_tab': 'admin_students',
        'form': form,
        'title': 'Bulk Upload Students',
    }
    return render(request, 'admin/bulk_upload.html', context)


@login_required
@user_passes_test(is_admin)
def organisation_management(request):
    """Manage organisations"""
    organisations = Organisation.objects.all()
    
    # Filters
    org_type = request.GET.get('type')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if org_type:
        organisations = organisations.filter(organisation_type=org_type)
    if status:
        organisations = organisations.filter(status=status)
    if search:
        organisations = organisations.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(city__icontains=search) |
            Q(state__icontains=search) |
            Q(area_of_work__icontains=search)
        )
    
    paginator = Paginator(organisations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'admin_companies',
        'organisations': page_obj,
        'type_choices': Organisation.TYPE_CHOICES,
        'total_count': organisations.count(),
        'search': search,
        'selected_type': org_type,
        'selected_status': status,
    }
    return render(request, 'admin/organisations.html', context)


@login_required
@user_passes_test(is_admin)
def add_organisation(request):
    """Add new organisation"""
    if request.method == 'POST':
        form = OrganisationForm(request.POST)
        if form.is_valid():
            organisation = form.save()
            messages.success(request, f'Organisation {organisation.name} added successfully!')
            return redirect('admin_companies')
    else:
        form = OrganisationForm()
    
    context = {
        'active_tab': 'admin_companies',
        'form': form,
        'title': 'Add Organisation',
    }
    return render(request, 'admin/organisation_form.html', context)


@login_required
@user_passes_test(is_admin)
def edit_organisation(request, org_id):
    """Edit organisation"""
    organisation = get_object_or_404(Organisation, id=org_id)
    
    if request.method == 'POST':
        form = OrganisationForm(request.POST, instance=organisation)
        if form.is_valid():
            form.save()
            messages.success(request, f'Organisation {organisation.name} updated successfully!')
            return redirect('admin_companies')
    else:
        form = OrganisationForm(instance=organisation)
    
    context = {
        'active_tab': 'admin_companies',
        'form': form,
        'organisation': organisation,
        'title': 'Edit Organisation',
    }
    return render(request, 'admin/organisation_form.html', context)


@login_required
@user_passes_test(is_admin)
def toggle_organisation_status(request, org_id):
    organisation = get_object_or_404(Organisation, id=org_id)
    organisation.status = 'inactive' if organisation.status == 'active' else 'active'
    organisation.save()
    messages.success(request, f'Organisation {organisation.name} status changed to {organisation.status}.')
    return redirect('admin_companies')


@login_required
@user_passes_test(is_admin)
def organisation_detail(request, org_id):
    organisation = get_object_or_404(Organisation, id=org_id)
    internships = organisation.internship_records.select_related('student', 'student__programme', 'student__batch').all()
    students = Student.objects.filter(internship_records__organisation=organisation).distinct()
    
    context = {
        'active_tab': 'admin_companies',
        'organisation': organisation,
        'internships': internships,
        'students': students,
    }
    return render(request, 'admin/organisation_detail.html', context)


@login_required
@user_passes_test(is_admin)
def programme_management(request):
    """Manage programmes"""
    programmes = Programme.objects.all()
    
    context = {
        'active_tab': 'admin_programmes',
        'programmes': programmes,
    }
    return render(request, 'admin/programmes.html', context)


@login_required
@user_passes_test(is_admin)
def add_programme(request):
    """Add new programme"""
    if request.method == 'POST':
        form = ProgrammeForm(request.POST)
        if form.is_valid():
            programme = form.save()
            messages.success(request, f'Programme {programme.name} added successfully!')
            return redirect('admin_programmes')
    else:
        form = ProgrammeForm()
    
    context = {
        'form': form,
        'title': 'Add Programme',
    }
    return render(request, 'admin/programme_form.html', context)


@login_required
@user_passes_test(is_admin)
def batch_management(request):
    """Manage batches"""
    batches = Batch.objects.select_related('programme').all()
    
    context = {
        'active_tab': 'admin_batches',
        'batches': batches,
    }
    return render(request, 'admin/batches.html', context)


@login_required
@user_passes_test(is_admin)
def add_batch(request):
    """Add new batch"""
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'Batch {batch.batch_year} added successfully!')
            return redirect('admin_batches')
    else:
        form = BatchForm()
    
    context = {
        'form': form,
        'title': 'Add Batch',
    }
    return render(request, 'admin/batch_form.html', context)


@login_required
@user_passes_test(is_admin)
def assessment_config(request):
    """Configure assessment rules"""
    configs = AssessmentConfiguration.objects.select_related('programme').all()
    
    context = {
        'active_tab': 'admin_config',
        'configs': configs,
    }
    return render(request, 'admin/assessment_config.html', context)


@login_required
@user_passes_test(is_admin)
def add_assessment_config(request):
    """Add assessment configuration"""
    if request.method == 'POST':
        form = AssessmentConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, f'Configuration for {config.programme.name} added successfully!')
            return redirect('admin_assessment_config')
    else:
        form = AssessmentConfigurationForm()
    
    context = {
        'form': form,
        'title': 'Add Assessment Configuration',
    }
    return render(request, 'admin/config_form.html', context)


@login_required
@user_passes_test(is_admin)
def view_student_detail(request, student_id):
    """View complete student profile with all records"""
    student = get_object_or_404(Student, id=student_id)
    internships = student.internship_records.all().order_by('internship_number')
    breaks = student.breaks.all().order_by('-start_date')
    mentors = student.mentor_assignments.all().order_by('-effective_from')
    
    # Calculate consolidated marks
    consolidated_data = calculate_student_consolidated_marks(student)
    
    context = {
        'active_tab': 'admin_students',
        'student': student,
        'internships': internships,
        'breaks': breaks,
        'mentors': mentors,
        'consolidated_data': consolidated_data,
    }
    return render(request, 'admin/student_detail.html', context)


@login_required
@user_passes_test(is_admin)
def user_management(request):
    """Manage system users"""
    users = User.objects.all().order_by('-date_joined')
    
    context = {
        'active_tab': 'admin_users',
        'users': users,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'admin/users.html', context)


@login_required
@user_passes_test(is_admin)
def add_user(request):
    """Add a new system user"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('admin_users')
    else:
        form = UserRegistrationForm()

    context = {
        'active_tab': 'admin_users',
        'form': form,
        'title': 'Add New User',
    }
    return render(request, 'admin/user_form.html', context)


@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """Activate/deactivate user"""
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} {status} successfully!')
    return redirect('admin_users')

# admin_views.py - Add these functions

@login_required
@user_passes_test(is_admin)
def pending_users(request):
    """View and approve pending user registrations"""
    pending_users = User.objects.filter(role='pending', is_active=False).order_by('-date_joined')
    
    context = {
        'active_tab': 'admin_pending_users',
        'pending_users': pending_users,
        'total_pending': pending_users.count(),
    }
    return render(request, 'admin/pending_users.html', context)


@login_required
@user_passes_test(is_admin)
def approve_user(request, user_id):
    """Approve a user and assign role"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        role = request.POST.get('role')
        user.role = role
        user.is_active = True
        user.save()
        
        # If role is student, create student profile
        if role == 'student':
            # Check if student profile exists, if not create placeholder
            if not hasattr(user, 'student_profile'):
                messages.warning(request, f'Student profile for {user.email} needs to be created separately.')
        
        messages.success(request, f'User {user.email} approved as {user.get_role_display()}')
        return redirect('admin_pending_users')
    
    context = {
        'user': user,
        'role_choices': [('student', 'Student'), ('faculty_mentor', 'Faculty Mentor'), 
                        ('faculty_evaluator', 'Faculty Evaluator'), ('dept_admin', 'Department Admin'),
                        ('hod', 'HoD')],
    }
    return render(request, 'admin/approve_user.html', context)


@login_required
@user_passes_test(is_admin)
def reject_user(request, user_id):
    """Reject a pending user registration"""
    user = get_object_or_404(User, id=user_id, role='pending')
    user.delete()
    messages.success(request, f'User registration rejected and deleted.')
    return redirect('admin_pending_users')


@login_required
@user_passes_test(is_admin)
def manage_user_roles(request):
    """Manage existing users and their roles"""
    users = User.objects.exclude(role='pending').order_by('-date_joined')
    
    context = {
        'active_tab': 'admin_users',
        'users': users,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'admin/manage_users.html', context)


@login_required
@user_passes_test(is_admin)
def update_user_role(request, user_id):
    """Update user role"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        role = request.POST.get('role')
        user.role = role
        user.save()
        messages.success(request, f'Role updated to {user.get_role_display()}')
        return redirect('admin_manage_users')
    
    context = {
        'user': user,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'admin/update_role.html', context)