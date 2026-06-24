# apps/core/admin_views.py - CONSOLIDATED VERSION

# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.admin.views.decorators import staff_member_required
# from django.contrib.auth.decorators import login_required, user_passes_test
# from django.contrib import messages
# from django.core.paginator import Paginator
# from django.db.models import Count, Q, Avg, Sum
# from django.http import JsonResponse, HttpResponse
# from django.utils import timezone
# from django.db.models import F
# # import pandas as pd
# import json
# import csv
# from datetime import datetime

# # User model - Use the correct one
# from django.contrib.auth.models import User
# from apps.authentication.models import UserProfile

# from .models import (
#     Programme, Batch, Student, Organisation, 
#     InternshipRecord, BreakRecord,
#     MentorAssignment, AssessmentComponent, AssessmentMarks, ConsolidatedScore
# )
# from .forms import (
#     UserForm, StudentForm, OrganisationForm, InternshipForm, 
#     BreakForm, MentorAssignmentForm, AssessmentMarksForm,
#     AssessmentComponentForm, ProgrammeForm, BatchForm, ProfileForm
# )
# from .decorators import admin_required

# # Import utilities from apps/utils
# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from apps.utils.permissions import is_admin, is_dept_admin
# from apps.utils.calculations import calculate_student_consolidated_marks
# from apps.utils.report_generator import generate_excel_report, generate_pdf_report
# from apps.utils.notifications import send_notification

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
import csv
from datetime import datetime

# User model - Use the correct one
from django.contrib.auth.models import User
from apps.authentication.models import UserProfile

from .models import (
    Department, Programme, Batch, Student, Organisation, 
    InternshipRecord, BreakRecord,
    MentorAssignment, AssessmentComponent, AssessmentMarks, ConsolidatedScore
)
from .forms import (
    UserForm, StudentForm, OrganisationForm, InternshipForm, 
    BreakForm, MentorAssignmentForm, AssessmentMarksForm,
    AssessmentComponentForm, ProgrammeForm, BatchForm, ProfileForm, DepartmentForm,
    ADMIN_MANAGED_ROLE_CHOICES
)
from .decorators import admin_required

# Import utilities from apps/utils
from apps.utils.permissions import is_admin, is_dept_admin, is_hod
from apps.utils.calculations import calculate_student_consolidated_marks
from apps.utils.report_generator import generate_excel_report, generate_pdf_report
from apps.utils.notifications import send_notification


# ============================================
# ADMIN DASHBOARD
# ============================================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin Dashboard with statistics"""
    context = {
        'active_tab': 'admin_dashboard',
        'total_users': UserProfile.objects.count(),
        'total_students': Student.objects.count(),
        'active_students': Student.objects.filter(status='active').count(),
        'total_organisations': Organisation.objects.filter(is_active=True).count(),
        'total_internships': InternshipRecord.objects.count(),
        'completed_internships': InternshipRecord.objects.filter(completion_status='completed').count(),
        'pending_verifications': InternshipRecord.objects.filter(verification_status='submitted').count(),
        'pending_marks': AssessmentMarks.objects.filter(status='submitted').count(),
        'pending_approvals': InternshipRecord.objects.filter(verification_status='verified', completion_status='pending').count(),
        'recent_students': Student.objects.all().order_by('-created_on')[:10],
        'recent_internships': InternshipRecord.objects.all().order_by('-created_on')[:10],
        'internship_by_status': InternshipRecord.objects.values('verification_status').annotate(count=Count('id')),
        'internship_by_type': InternshipRecord.objects.values('internship_type').annotate(count=Count('id')),
    }
    return render(request, 'admin/dashboard.html', context)


# ============================================
# USER MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def user_list(request):
    """Manage non-student system users."""
    users = UserProfile.objects.exclude(role='student').select_related('user', 'department')
    
    # Filters
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    users = users.order_by('-created_on')
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'admin_users',
        'users': page_obj,
        'roles': ADMIN_MANAGED_ROLE_CHOICES,
        'departments': Department.objects.filter(is_active=True),
        'total_count': users.count(),
        'filter_values': {
            'role': role_filter,
            'search': search,
        },
    }
    return render(request, 'admin/users.html', context)


@login_required
@user_passes_test(is_admin)
def user_add(request):
    """Add new user"""
    if request.method == 'POST':
        if request.POST.get('role') == 'student':
            messages.error(request, 'Students must be added from Student Management.')
            return redirect('admin_users')
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
        return redirect('admin_users')
    
    return redirect('admin_users')


@login_required
@user_passes_test(is_admin)
def user_edit(request, pk):
    """Edit user details and role"""
    profile = get_object_or_404(UserProfile, pk=pk)
    if profile.role == 'student':
        messages.error(request, 'Student details must be edited from Student Management.')
        return redirect('admin_students')
    user = profile.user
    
    if request.method == 'POST':
        if request.POST.get('role') == 'student':
            messages.error(request, 'User Management cannot convert accounts into student records. Use Student Management.')
            return redirect('admin_users')
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
        return redirect('admin_users')
    
    # GET request - render modal content
    form = UserForm(instance=user)
    form.fields['role'].initial = profile.role
    form.fields['phone_number'].initial = profile.phone_number
    form.fields['is_active'].initial = profile.is_active
    return render(request, 'admin/user_form_modal_content.html', {'form': form, 'edit': True, 'profile': profile})


@login_required
@user_passes_test(is_admin)
def user_toggle(request, pk):
    """Activate/deactivate user"""
    profile = get_object_or_404(UserProfile, pk=pk)
    if profile.role == 'student':
        messages.error(request, 'Student account status must be handled from Student Management.')
        return redirect('admin_students')
    profile.is_active = not profile.is_active
    profile.save()
    status = "activated" if profile.is_active else "deactivated"
    messages.success(request, f'User {profile.user.email} {status} successfully!')
    return redirect('admin_users')


@login_required
@user_passes_test(is_admin)
def user_approve(request, pk):
    """Approve a pending user"""
    profile = get_object_or_404(UserProfile, pk=pk)
    if profile.role == 'student':
        messages.error(request, 'Student approval/details must be handled from Student Management.')
        return redirect('admin_students')
    if request.method in ['GET', 'POST']:
        profile.is_approved = True
        profile.save()
        # Send notification
        send_notification(
            profile.user,
            "Account Approved",
            f"Your account has been approved. You can now login with role: {profile.get_role_display()}",
            "success"
        )
        messages.success(request, f'User {profile.user.email} approved successfully!')
        return redirect('admin_users')
    return redirect('admin_users')


@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    """Soft delete user"""
    profile = get_object_or_404(UserProfile, pk=pk)
    if profile.role == 'student':
        messages.error(request, 'Student records must be handled from Student Management.')
        return redirect('admin_students')
    if request.method in ['GET', 'POST']:
        profile.is_active = False
        profile.save()
        messages.success(request, f'User {profile.user.email} deactivated successfully!')
        return redirect('admin_users')
    return redirect('admin_users')


@login_required
@user_passes_test(is_admin)
def bulk_upload_users(request):
    """Bulk upload users via CSV"""
    if request.method == 'POST':
        uploaded_file = request.FILES.get('csv_file')
        if not uploaded_file:
            messages.error(request, 'Please select a CSV file')
            return redirect('admin_users')
        
        if not uploaded_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin_users')
        
        try:
            decoded = uploaded_file.read().decode('utf-8-sig')
            csv_reader = csv.DictReader(decoded.splitlines())
            
            created_count = 0
            failed_rows = []
            
            for row_num, row in enumerate(csv_reader, 2):
                try:
                    email = row.get('EMAIL', '').strip().lower()
                    if not email:
                        raise ValueError("Email is required")
                    
                    if User.objects.filter(email=email).exists():
                        raise ValueError(f"Email {email} already exists")
                    
                    password = User.objects.make_random_password()
                    
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        first_name=row.get('FIRST_NAME', '').strip(),
                        last_name=row.get('LAST_NAME', '').strip(),
                        password=password,
                        is_staff=False
                    )
                    
                    role = row.get('ROLE', '').strip().lower()
                    allowed_roles = [role_code for role_code, _ in ADMIN_MANAGED_ROLE_CHOICES]
                    if role not in allowed_roles:
                        raise ValueError("ROLE must be one of: " + ", ".join(allowed_roles))
                    
                    UserProfile.objects.create(
                        user=user,
                        role=role,
                        phone_number=row.get('PHONE', '').strip(),
                        is_active=True,
                        is_approved=True
                    )
                    
                    created_count += 1
                    
                except Exception as e:
                    failed_rows.append({'row': row_num, 'error': str(e)})
            
            if created_count > 0:
                messages.success(request, f'Successfully created {created_count} user(s)')
            
            if failed_rows:
                messages.warning(request, f'Failed to create {len(failed_rows)} user(s)')
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
        
        return redirect('admin_users')
    
    return redirect('admin_users')


# ============================================
# PENDING USERS (Google Login Approval)
# ============================================

@login_required
@user_passes_test(is_admin)
def pending_users(request):
    """View and approve pending user registrations (from Google Login)"""
    pending_users = UserProfile.objects.filter(
        is_approved=False,
        is_active=True
    ).exclude(role='student').select_related('user', 'department')
    
    context = {
        'active_tab': 'admin_pending_users',
        'pending_users': pending_users,
        'total_pending': pending_users.count(),
    }
    return render(request, 'admin/pending_users.html', context)


@login_required
@user_passes_test(is_admin)
def approve_user(request, user_id):
    """Approve a user and assign role (for Google Login users)"""
    profile = get_object_or_404(UserProfile, user_id=user_id)
    user = profile.user
    if profile.role == 'student':
        messages.error(request, 'Student requests must be approved from Student Management.')
        return redirect('admin_students')
    
    if request.method == 'POST':
        role = request.POST.get('role')
        if role == 'student':
            messages.error(request, 'Student requests must be approved from Student Management.')
            return redirect('admin_students')
        profile.role = role
        profile.is_approved = True
        profile.save()
        
        # Send notification
        send_notification(
            user,
            "Account Approved",
            f"Your account has been approved. You are now registered as {profile.get_role_display()}.",
            "success"
        )
        
        messages.success(request, f'User {user.email} approved as {profile.get_role_display()}')
        return redirect('admin_users')
    
    context = {
        'user': user,
        'profile': profile,
        'role_choices': ADMIN_MANAGED_ROLE_CHOICES,
    }
    return render(request, 'admin/approve_user.html', context)


@login_required
@user_passes_test(is_admin)
def reject_user(request, user_id):
    """Reject a pending user registration"""
    profile = get_object_or_404(UserProfile, user_id=user_id)
    if profile.role == 'student':
        messages.error(request, 'Student requests must be rejected from Student Management.')
        return redirect('admin_students')
    user = profile.user
    
    # Delete user and profile
    user.delete()
    messages.success(request, f'User registration rejected and deleted.')
    return redirect('admin_users')


@login_required
@user_passes_test(is_admin)
def user_bulk_upload_sample(request):
    """Download sample CSV for non-student user bulk upload."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_bulk_upload_sample.csv"'
    writer = csv.writer(response)
    writer.writerow(['FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONE', 'ROLE'])
    writer.writerow(['Anita', 'Rao', 'anita.rao@example.com', '9876543210', 'faculty_mentor'])
    writer.writerow(['Vikram', 'Menon', 'vikram.menon@example.com', '9876543211', 'evaluator'])
    return response


@login_required
@user_passes_test(is_admin)
def manage_user_roles(request):
    """Manage existing users and their roles"""
    users = UserProfile.objects.filter(is_approved=True).exclude(role='pending').select_related('user')
    
    context = {
        'active_tab': 'admin_users',
        'users': users,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    return render(request, 'admin/manage_users.html', context)


@login_required
@user_passes_test(is_admin)
def update_user_role(request, user_id):
    """Update user role"""
    profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if request.method == 'POST':
        role = request.POST.get('role')
        profile.role = role
        profile.save()
        messages.success(request, f'Role updated to {profile.get_role_display()}')
        return redirect('admin_manage_users')
    
    context = {
        'profile': profile,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    return render(request, 'admin/update_role.html', context)


# ============================================
# STUDENT MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def student_list(request):
    """Manage students - list, add, edit, delete"""
    students = Student.objects.select_related('department', 'programme', 'batch', 'user').all()
    
    # Filters
    programme = request.GET.get('programme')
    batch = request.GET.get('batch')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if programme:
        students = students.filter(programme_id=programme)
    if batch:
        students = students.filter(batch_id=batch)
    if status:
        students = students.filter(status=status)
    if search:
        students = students.filter(
            Q(register_number__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )
    
    students = students.order_by('register_number')
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'admin_students',
        'students': page_obj,
        'pending_student_requests': UserProfile.objects.filter(
            role='student',
            is_approved=False,
            user__student_profile__isnull=True,
        ).select_related('user', 'department').order_by('-created_on'),
        'programmes': Programme.objects.filter(is_active=True),
        'batches': Batch.objects.filter(is_active=True),
        'departments': Department.objects.filter(is_active=True),
        'status_choices': Student.STATUS_CHOICES,
        'total_count': students.count(),
    }
    return render(request, 'admin/students.html', context)


@login_required
@user_passes_test(is_admin)
def student_add(request):
    """Add new student"""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                student = form.save()
                messages.success(request, f'Student {student.name} added successfully!')
                return redirect('admin_students')
            except Exception as e:
                messages.error(request, f'Error adding student: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_students')
    
    return redirect('admin_students')


@login_required
@user_passes_test(is_admin)
def student_request_approve(request, pk):
    """Approve a pending student login request and create an editable student row."""
    profile = get_object_or_404(
        UserProfile.objects.select_related('user'),
        pk=pk,
        role='student',
        is_approved=False,
    )
    try:
        if hasattr(profile.user, 'student_profile'):
            student = profile.user.student_profile
        else:
            base_register_number = f"PENDING-{str(profile.id)[:8].upper()}"
            register_number = base_register_number
            counter = 1
            while Student.objects.filter(register_number=register_number).exists():
                counter += 1
                register_number = f"{base_register_number}-{counter}"

            full_name = profile.user.get_full_name().strip()
            student = Student.objects.create(
                register_number=register_number,
                name=full_name or profile.user.email,
                email=profile.user.email,
                mobile=profile.phone_number or '',
                department=profile.department,
                programme=None,
                batch=None,
                degree_start_date=None,
                status='active',
                remarks='Created from approved student request. Complete academic details from Student Management.',
                user=profile.user,
                created_by=request.user,
            )
        profile.role = 'student'
        profile.department = student.department
        profile.phone_number = student.mobile or profile.phone_number
        profile.is_active = True
        profile.is_approved = True
        profile.save()
        send_notification(
            profile.user,
            "Student Account Approved",
            "Your student account has been approved. Academic details will be maintained by the administration.",
            "success"
        )
        messages.success(request, f'Student request approved. {student.name} is now listed in Student Management.')
    except Exception as e:
        messages.error(request, f'Error approving student request: {str(e)}')
    return redirect('admin_students')


@login_required
@user_passes_test(is_admin)
def student_request_reject(request, pk):
    """Reject a pending student login request."""
    profile = get_object_or_404(
        UserProfile.objects.select_related('user'),
        pk=pk,
        role='student',
        is_approved=False,
    )
    email = profile.user.email
    profile.is_active = False
    profile.save(update_fields=['is_active', 'updated_on'])
    messages.success(request, f'Student request {email} rejected. It remains available for approval later.')
    return redirect('admin_students')


@login_required
@user_passes_test(is_admin)
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
        return redirect('admin_students')
    
    return redirect('admin_students')


@login_required
@user_passes_test(is_admin)
def student_detail(request, pk):
    """View complete student profile with all records"""
    student = get_object_or_404(Student.objects.select_related('department', 'programme', 'batch'), pk=pk)
    internships = student.internships.select_related('organisation').all().order_by('internship_number')
    breaks = student.breaks.all().order_by('-start_date')
    mentors = student.mentor_assignments.select_related('faculty_mentor__user').all().order_by('-effective_from')
    consolidated_data = calculate_student_consolidated_marks(student)

    return JsonResponse({
        'register_number': student.register_number,
        'name': student.name,
        'email': student.email,
        'mobile': student.mobile or '-',
        'department': student.department.name if student.department else '-',
        'programme': student.programme.name if student.programme else '-',
        'batch': student.batch.name if student.batch else '-',
        'degree_start_date': student.degree_start_date.strftime('%d %b %Y') if student.degree_start_date else '-',
        'degree_end_date': student.degree_end_date.strftime('%d %b %Y') if student.degree_end_date else '-',
        'status': student.get_status_display(),
        'remarks': student.remarks or '-',
        'current_mentor': next(
            (
                assignment.faculty_mentor.user.get_full_name() or assignment.faculty_mentor.user.email
                for assignment in mentors
                if assignment.is_active
            ),
            '-'
        ),
        'mentor_history': [
            {
                'mentor': assignment.faculty_mentor.user.get_full_name() or assignment.faculty_mentor.user.email,
                'effective_from': assignment.effective_from.strftime('%d %b %Y'),
                'effective_to': assignment.effective_to.strftime('%d %b %Y') if assignment.effective_to else 'Current',
                'level': assignment.get_assignment_level_display(),
                'semester': assignment.related_semester or '-',
                'active': assignment.is_active,
            }
            for assignment in mentors
        ],
        'internships': [
            {
                'number': internship.internship_number,
                'organisation': internship.organisation.name,
                'type': internship.get_internship_type_display(),
                'start_date': internship.start_date.strftime('%d %b %Y'),
                'end_date': internship.end_date.strftime('%d %b %Y'),
                'status': internship.get_completion_status_display(),
                'verification': internship.get_verification_status_display(),
            }
            for internship in internships
        ],
        'break_count': breaks.count(),
        'consolidated_data': consolidated_data,
    })


@login_required
@user_passes_test(is_admin)
def student_delete(request, pk):
    """Soft delete student"""
    student = get_object_or_404(Student, pk=pk)
    if request.method in ['GET', 'POST']:
        student.status = 'discontinued'
        student.save()
        messages.success(request, f'Student {student.name} marked as discontinued!')
        return redirect('admin_students')
    return redirect('admin_students')


# @login_required
# @user_passes_test(is_admin)
# def bulk_upload_students(request):
#     """Bulk upload students via Excel/CSV"""
#     if request.method == 'POST':
#         uploaded_file = request.FILES.get('excel_file')
#         if not uploaded_file:
#             messages.error(request, 'Please select a file')
#             return redirect('admin_students')
        
#         try:
#             if uploaded_file.name.endswith('.csv'):
#                 df = pd.read_csv(uploaded_file)
#             else:
#                 df = pd.read_excel(uploaded_file)
            
#             success_count = 0
#             error_count = 0
            
#             for index, row in df.iterrows():
#                 try:
#                     programme = Programme.objects.get(code=str(row['programme_code']).strip())
#                     batch = Batch.objects.get(name=str(row['batch']).strip(), programme=programme)
                    
#                     student = Student(
#                         register_number=str(row['register_number']).strip(),
#                         name=row['name'],
#                         email=row['email'],
#                         programme=programme,
#                         batch=batch,
#                         degree_start_date=pd.to_datetime(row['degree_start_date']).date(),
#                         degree_end_date=pd.to_datetime(row['degree_end_date']).date(),
#                         mobile=str(row.get('mobile', '')).strip() if 'mobile' in row else '',
#                     )
#                     student.save()
#                     success_count += 1
#                 except Exception as e:
#                     error_count += 1
#                     print(f"Error at row {index}: {e}")
            
#             messages.success(request, f'Successfully uploaded {success_count} students. Errors: {error_count}')
#         except Exception as e:
#             messages.error(request, f'Error processing file: {str(e)}')
        
#         return redirect('admin_students')
    
#     return redirect('admin_students')
@login_required
@user_passes_test(is_admin)
def bulk_upload_students(request):
    """Bulk upload students via Excel/CSV"""
    if request.method == 'POST':
        uploaded_file = request.FILES.get('excel_file') or request.FILES.get('csv_file')
        if not uploaded_file:
            messages.error(request, 'Please select a file')
            return redirect('admin_students')
        
        # Check file extension
        filename = uploaded_file.name
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            messages.error(request, 'Please upload CSV or Excel file')
            return redirect('admin_students')
        
        try:
            # Try using pandas (preferred)
            try:
                import pandas as pd
                if filename.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Process using pandas
                success_count = 0
                error_count = 0
                
                for index, row in df.iterrows():
                    try:
                        programme = Programme.objects.get(code=str(row['programme_code']).strip())
                        batch = Batch.objects.get(name=str(row['batch']).strip(), programme=programme)
                        
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
                
            except ImportError:
                # Fallback: Use manual CSV/Excel parsing if pandas not installed
                messages.error(request, 'pandas is not installed. Please install pandas for bulk upload.')
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
        
        return redirect('admin_students')
    
    return redirect('admin_students')


@login_required
@user_passes_test(is_admin)
def student_bulk_upload_sample(request):
    """Download sample CSV for student bulk upload."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_bulk_upload_sample.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'register_number', 'name', 'email', 'mobile',
        'programme_code', 'batch', 'degree_start_date', 'degree_end_date'
    ])
    writer.writerow([
        'REG001', 'Priya Sharma', 'priya.sharma@example.com', '9876543212',
        'BA.LLB', '2026 Batch', '2026-07-01', '2031-06-30'
    ])
    return response


# ============================================
# ORGANISATION MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def organisation_list(request):
    """Manage organisations"""
    organisations = Organisation.objects.all()
    
    # Filters
    org_type = request.GET.get('type')
    search = request.GET.get('search')
    
    if org_type:
        organisations = organisations.filter(organisation_type=org_type)
    if search:
        organisations = organisations.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(city__icontains=search) |
            Q(state__icontains=search) |
            Q(address__icontains=search) |
            Q(area_of_work__icontains=search)
        )
    
    paginator = Paginator(organisations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'admin_organisations',
        'organisations': page_obj,
        'types': Organisation.TYPE_CHOICES,
        'total_count': organisations.count(),
    }
    return render(request, 'admin/organisations.html', context)


@login_required
@user_passes_test(is_admin)
def organisation_add(request):
    """Add new organisation"""
    if request.method == 'POST':
        form = OrganisationForm(request.POST)
        if form.is_valid():
            try:
                organisation = form.save()
                messages.success(request, f'Organisation {organisation.name} added successfully!')
                return redirect('admin_organisations')
            except Exception as e:
                messages.error(request, f'Error adding organisation: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_organisations')
    
    return redirect('admin_organisations')


@login_required
@user_passes_test(is_admin)
def organisation_edit(request, pk):
    """Edit organisation"""
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
        return redirect('admin_organisations')
    
    return redirect('admin_organisations')


@login_required
@user_passes_test(is_admin)
def organisation_toggle(request, pk):
    """Toggle organisation active status"""
    organisation = get_object_or_404(Organisation, pk=pk)
    organisation.is_active = not organisation.is_active
    organisation.save()
    status = "activated" if organisation.is_active else "deactivated"
    messages.success(request, f'Organisation {organisation.name} {status} successfully!')
    return redirect('admin_organisations')


@login_required
@user_passes_test(is_admin)
def organisation_delete(request, pk):
    """Soft delete organisation"""
    organisation = get_object_or_404(Organisation, pk=pk)
    organisation.is_active = False
    organisation.save()
    messages.success(request, f'Organisation {organisation.name} deactivated successfully!')
    return redirect('admin_organisations')


@login_required
@user_passes_test(is_admin)
def organisation_detail(request, pk):
    """Return organisation details for modal."""
    organisation = get_object_or_404(Organisation, pk=pk)
    internships_count = organisation.internships.count()

    return JsonResponse({
        'name': organisation.name,
        'type': organisation.type_display,
        'contact_person': organisation.contact_person or '-',
        'designation': organisation.designation or '-',
        'email': organisation.email or '-',
        'phone': organisation.phone or '-',
        'address': organisation.address or '-',
        'city': organisation.city or '-',
        'state': organisation.state or '-',
        'website': organisation.website or '-',
        'area_of_work': organisation.area_of_work or '-',
        'feedback_rating': str(organisation.feedback_rating) if organisation.feedback_rating is not None else '-',
        'remarks': organisation.remarks or '-',
        'status': 'Active' if organisation.is_active else 'Inactive',
        'internships_count': internships_count,
        'students': [
            {
                'register_number': item.student.register_number,
                'name': item.student.name,
                'programme': item.student.programme.name if item.student.programme else '-',
                'batch': item.student.batch.name if item.student.batch else '-',
                'period': f"{item.start_date.strftime('%d %b %Y')} - {item.end_date.strftime('%d %b %Y')}",
            }
            for item in organisation.internships.select_related('student', 'student__programme', 'student__batch').order_by('-start_date')[:50]
        ],
    })


# ============================================
# PROGRAMME MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def programme_list(request):
    """Manage programmes"""
    programmes = Programme.objects.all()
    
    context = {
        'active_tab': 'admin_programmes',
        'programmes': programmes,
    }
    return render(request, 'admin/programmes.html', context)


@login_required
@user_passes_test(is_admin)
def department_list(request):
    """Manage departments"""
    departments = Department.objects.all().order_by('name')
    return render(request, 'admin/departments.html', {
        'active_tab': 'admin_departments',
        'departments': departments,
    })


@login_required
@user_passes_test(is_admin)
def department_add(request):
    """Add department"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    return redirect('admin_departments')


@login_required
@user_passes_test(is_admin)
def department_edit(request, pk):
    """Edit department"""
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    return redirect('admin_departments')


@login_required
@user_passes_test(is_admin)
def department_toggle(request, pk):
    """Activate/deactivate department"""
    department = get_object_or_404(Department, pk=pk)
    department.is_active = not department.is_active
    department.save(update_fields=['is_active', 'updated_on'])
    status = 'activated' if department.is_active else 'deactivated'
    messages.success(request, f'Department {status} successfully!')
    return redirect('admin_departments')


@login_required
@user_passes_test(is_admin)
def programme_add(request):
    """Add new programme"""
    if request.method == 'POST':
        form = ProgrammeForm(request.POST)
        if form.is_valid():
            try:
                programme = form.save()
                messages.success(request, f'Programme {programme.name} added successfully!')
                return redirect('admin_programmes')
            except Exception as e:
                messages.error(request, f'Error adding programme: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_programmes')
    
    return redirect('admin_programmes')


@login_required
@user_passes_test(is_admin)
def programme_edit(request, pk):
    """Edit programme"""
    programme = get_object_or_404(Programme, pk=pk)
    
    if request.method == 'POST':
        form = ProgrammeForm(request.POST, instance=programme)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Programme {programme.name} updated successfully!')
                return redirect('admin_programmes')
            except Exception as e:
                messages.error(request, f'Error updating programme: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_programmes')
    
    return redirect('admin_programmes')


@login_required
@user_passes_test(is_admin)
def programme_toggle(request, pk):
    """Toggle programme active status"""
    programme = get_object_or_404(Programme, pk=pk)
    programme.is_active = not programme.is_active
    programme.save()
    status = "activated" if programme.is_active else "deactivated"
    messages.success(request, f'Programme {programme.name} {status} successfully!')
    return redirect('admin_programmes')


@login_required
@user_passes_test(is_admin)
def programme_delete(request, pk):
    """Delete programme"""
    programme = get_object_or_404(Programme, pk=pk)
    programme.delete()
    messages.success(request, f'Programme {programme.name} deleted successfully!')
    return redirect('admin_programmes')


@login_required
@user_passes_test(is_admin)
def programme_detail(request, pk):
    """Return programme details for modal."""
    programme = get_object_or_404(Programme, pk=pk)
    return JsonResponse({
        'name': programme.name,
        'code': programme.code,
        'duration_years': programme.duration_years,
        'status': 'Active' if programme.is_active else 'Inactive',
        'batches_count': programme.batches.count(),
        'students_count': programme.students.count(),
        'created_on': programme.created_on.strftime('%d %b %Y'),
    })


# ============================================
# BATCH MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def batch_list(request):
    """Manage batches"""
    batches = Batch.objects.select_related('programme').all()
    
    context = {
        'active_tab': 'admin_batches',
        'batches': batches,
        'programmes': Programme.objects.filter(is_active=True),
    }
    return render(request, 'admin/batches.html', context)


@login_required
@user_passes_test(is_admin)
def batch_add(request):
    """Add new batch"""
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            try:
                batch = form.save()
                messages.success(request, f'Batch {batch.name} added successfully!')
                return redirect('admin_batches')
            except Exception as e:
                messages.error(request, f'Error adding batch: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_batches')
    
    return redirect('admin_batches')


@login_required
@user_passes_test(is_admin)
def batch_edit(request, pk):
    """Edit batch"""
    batch = get_object_or_404(Batch, pk=pk)
    
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Batch {batch.name} updated successfully!')
                return redirect('admin_batches')
            except Exception as e:
                messages.error(request, f'Error updating batch: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_batches')
    
    return redirect('admin_batches')


@login_required
@user_passes_test(is_admin)
def batch_toggle(request, pk):
    """Toggle batch active status"""
    batch = get_object_or_404(Batch, pk=pk)
    batch.is_active = not batch.is_active
    batch.save()
    status = "activated" if batch.is_active else "deactivated"
    messages.success(request, f'Batch {batch.name} {status} successfully!')
    return redirect('admin_batches')


@login_required
@user_passes_test(is_admin)
def batch_delete(request, pk):
    """Delete batch"""
    batch = get_object_or_404(Batch, pk=pk)
    batch.delete()
    messages.success(request, f'Batch {batch.name} deleted successfully!')
    return redirect('admin_batches')


@login_required
@user_passes_test(is_admin)
def batch_detail(request, pk):
    """Return batch details for modal."""
    batch = get_object_or_404(Batch.objects.select_related('programme'), pk=pk)
    return JsonResponse({
        'name': batch.name,
        'programme': batch.programme.name,
        'programme_code': batch.programme.code,
        'start_year': batch.start_year,
        'end_year': batch.end_year,
        'status': 'Active' if batch.is_active else 'Inactive',
        'students_count': batch.students.count(),
        'created_on': batch.created_on.strftime('%d %b %Y'),
    })


# ============================================
# INTERNSHIP MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def internship_list(request):
    """Manage internships"""
    internships = InternshipRecord.objects.select_related('student', 'organisation').all()
    
    # Filters
    internship_type = request.GET.get('type')
    if internship_type:
        internships = internships.filter(internship_type=internship_type)
    
    verification_status = request.GET.get('verification')
    if verification_status:
        internships = internships.filter(verification_status=verification_status)
    
    context = {
        'active_tab': 'admin_internships',
        'internships': internships,
        'types': InternshipRecord.INTERNSHIP_TYPES,
        'verification_statuses': InternshipRecord.VERIFICATION_STATUS,
    }
    return render(request, 'admin/internships.html', context)


@login_required
@user_passes_test(is_admin)
def internship_detail(request, pk):
    """Return internship details for modal."""
    internship = get_object_or_404(
        InternshipRecord.objects.select_related('student', 'organisation', 'created_by', 'updated_by', 'verified_by'),
        pk=pk
    )

    return JsonResponse({
        'student': f'{internship.student.name} ({internship.student.register_number})',
        'type': internship.get_internship_type_display(),
        'number': internship.internship_number,
        'academic_phase': internship.academic_phase or '-',
        'organisation': internship.organisation.name,
        'semester': internship.related_semester or '-',
        'period': f"{internship.start_date.strftime('%d %b %Y')} - {internship.end_date.strftime('%d %b %Y')}",
        'duration': f'{internship.duration} days' if internship.duration is not None else '-',
        'mode': internship.get_mode_display(),
        'completion_status': internship.get_completion_status_display(),
        'verification_status': internship.get_verification_status_display(),
        'submission_date': internship.submission_date.strftime('%d %b %Y') if internship.submission_date else '-',
        'document': internship.supporting_document.url if internship.supporting_document else '',
        'certificate': internship.certificate_upload.url if internship.certificate_upload else '',
        'report': internship.report_upload.url if internship.report_upload else '',
        'date_override': 'Yes' if internship.date_override_approved else 'No',
        'date_override_reason': internship.date_override_reason or '-',
        'break_overlap': 'Yes' if internship.has_break_overlap else 'No',
        'overlapping_breaks': [
            f"{break_record.get_break_type_display()} ({break_record.start_date.strftime('%d %b %Y')} - {break_record.end_date.strftime('%d %b %Y')})"
            for break_record in internship.overlapping_breaks
        ],
        'nature_of_work': internship.nature_of_work or '-',
        'remarks': internship.remarks or '-',
        'created_by': internship.created_by.get_full_name() or internship.created_by.email if internship.created_by else '-',
        'updated_by': internship.updated_by.get_full_name() or internship.updated_by.email if internship.updated_by else '-',
        'verified_by': internship.verified_by.get_full_name() or internship.verified_by.email if internship.verified_by else '-',
    })


@login_required
@user_passes_test(is_admin)
def internship_verify(request, pk):
    """Admin verification action for internship details."""
    internship = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in ['verified', 'needs_correction', 'rejected']:
            messages.error(request, 'Please choose a valid verification action.')
            return redirect('admin_internships')
        remarks = request.POST.get('remarks', '').strip()
        if action == 'needs_correction' and not remarks:
            messages.error(request, 'Please mention what changes are required.')
            return redirect('admin_internships')
        internship.verification_status = action
        internship.verified_by = request.user
        internship.verified_at = timezone.now()
        if remarks:
            internship.remarks = remarks
        internship.save(update_fields=['verification_status', 'verified_by', 'verified_at', 'remarks', 'updated_on'])
        messages.success(request, f'Internship marked as {internship.get_verification_status_display()}.')
    return redirect('admin_internships')


# ============================================
# BREAK MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def break_list(request):
    """Manage breaks"""
    breaks = BreakRecord.objects.select_related('student').all()
    
    context = {
        'active_tab': 'admin_breaks',
        'breaks': breaks,
        'students': Student.objects.all().order_by('register_number'),
        'approvers': User.objects.filter(
            profile__role__in=['admin', 'hod']
        ).order_by('first_name', 'last_name', 'email'),
    }
    return render(request, 'admin/breaks.html', context)


@login_required
@user_passes_test(is_admin)
def break_add(request):
    """Add new break"""
    if request.method == 'POST':
        student = get_object_or_404(Student, pk=request.POST.get('student'))
        form = BreakForm(request.POST, request.FILES, instance=BreakRecord(student=student))
        if form.is_valid():
            try:
                break_record = form.save(commit=False)
                break_record.save()
                overlaps = _break_overlapping_internships(break_record)
                if overlaps:
                    messages.warning(request, f'Break overlaps with {len(overlaps)} internship period(s).')
                messages.success(request, 'Break record added successfully!')
                return redirect('admin_breaks')
            except Exception as e:
                messages.error(request, f'Error adding break: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_breaks')
    
    return redirect('admin_breaks')


@login_required
@user_passes_test(is_admin)
def break_edit(request, pk):
    """Edit break"""
    break_record = get_object_or_404(BreakRecord, pk=pk)
    
    if request.method == 'POST':
        form = BreakForm(request.POST, request.FILES, instance=break_record)
        if form.is_valid():
            try:
                break_record = form.save()
                overlaps = _break_overlapping_internships(break_record)
                if overlaps:
                    messages.warning(request, f'Break overlaps with {len(overlaps)} internship period(s).')
                messages.success(request, 'Break record updated successfully!')
                return redirect('admin_breaks')
            except Exception as e:
                messages.error(request, f'Error updating break: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_breaks')
    
    return redirect('admin_breaks')


@login_required
@user_passes_test(is_admin)
def break_delete(request, pk):
    """Delete break"""
    break_record = get_object_or_404(BreakRecord, pk=pk)
    break_record.delete()
    messages.success(request, 'Break record deleted successfully!')
    return redirect('admin_breaks')


@login_required
@user_passes_test(is_admin)
def break_detail(request, pk):
    """Return break details for modal."""
    break_record = get_object_or_404(BreakRecord.objects.select_related('student', 'approved_by'), pk=pk)
    duration = (break_record.end_date - break_record.start_date).days
    overlaps = _break_overlapping_internships(break_record)
    return JsonResponse({
        'student': f'{break_record.student.register_number} - {break_record.student.name}',
        'break_type': break_record.get_break_type_display(),
        'start_date': break_record.start_date.strftime('%d %b %Y'),
        'end_date': break_record.end_date.strftime('%d %b %Y'),
        'duration': f'{duration} days',
        'approved_by': break_record.approved_by.get_full_name() or break_record.approved_by.email if break_record.approved_by else '-',
        'reason': break_record.reason or '-',
        'impact': break_record.impact_on_internship or '',
        'document': break_record.supporting_document.url if break_record.supporting_document else '',
        'remarks': break_record.remarks or '',
        'overlaps': [
            {
                'number': internship.internship_number,
                'organisation': internship.organisation.name,
                'period': f"{internship.start_date.strftime('%d %b %Y')} - {internship.end_date.strftime('%d %b %Y')}",
            }
            for internship in overlaps
        ],
    })


def _break_overlapping_internships(break_record):
    return list(
        break_record.student.internships.select_related('organisation').filter(
            start_date__lte=break_record.end_date,
            end_date__gte=break_record.start_date,
        )
    )


# ============================================
# ASSESSMENT CONFIGURATION
# ============================================

@login_required
@user_passes_test(is_admin)
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
        return redirect('admin_assessment_config')
    
    context = {
        'active_tab': 'admin_assessment_config',
        'components': components,
    }
    return render(request, 'admin/assessment_config.html', context)


@login_required
@user_passes_test(is_admin)
def assessment_component_delete(request, pk):
    """Delete assessment component"""
    component = get_object_or_404(AssessmentComponent, pk=pk)
    component.is_active = False
    component.save()
    messages.success(request, f'Component {component.name} deactivated successfully!')
    return redirect('admin_assessment_config')


@login_required
@user_passes_test(is_admin)
def assessment_component_detail(request, pk):
    """Return assessment component details for modal."""
    component = get_object_or_404(AssessmentComponent, pk=pk)
    return JsonResponse({
        'name': component.name,
        'assessment_type': component.get_assessment_type_display(),
        'default_max_marks': str(component.default_max_marks),
        'weightage': str(component.weightage),
        'is_mandatory': 'Yes' if component.is_mandatory else 'No',
        'status': 'Active' if component.is_active else 'Inactive',
        'created_on': component.created_on.strftime('%d %b %Y'),
    })


@login_required
@user_passes_test(is_admin)
def assessment_component_edit(request, pk):
    """Edit assessment component."""
    component = get_object_or_404(AssessmentComponent, pk=pk)

    if request.method == 'POST':
        form = AssessmentComponentForm(request.POST, instance=component)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Component {component.name} updated successfully!')
                return redirect('admin_assessment_config')
            except Exception as e:
                messages.error(request, f'Error updating component: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_assessment_config')

    return render(request, 'admin/assessment_component_form.html', {
        'component': component,
        'assessment_types': AssessmentComponent.ASSESSMENT_TYPES,
    })


# ============================================
# MENTOR ASSIGNMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def mentor_assignment_list(request):
    """Manage mentor assignments"""
    assignments = MentorAssignment.objects.select_related('student', 'faculty_mentor').all()
    faculty_mentors = UserProfile.objects.filter(role__in=['faculty_mentor', 'hod'])
    
    context = {
        'active_tab': 'admin_mentor_assignments',
        'assignments': assignments,
        'faculty_mentors': faculty_mentors,
        'students': Student.objects.all(),
    }
    return render(request, 'admin/mentor_assignments.html', context)


# @login_required
# @user_passes_test(is_admin)
# def mentor_assignment_add(request):
#     """Add mentor assignment via AJAX"""
#     if request.method == 'POST':
#         form = MentorAssignmentForm(request.POST)
#         if form.is_valid():
#             try:
#                 assignment = form.save(commit=False)
#                 assignment.assigned_by = request.user
#                 assignment.save()
#                 messages.success(request, 'Mentor assignment added successfully!')
#                 return JsonResponse({'success': True})
#             except Exception as e:
#                 return JsonResponse({'success': False, 'error': str(e)})
#         else:
#             return JsonResponse({'success': False, 'errors': form.errors})
    
#     return JsonResponse({'success': False, 'error': 'Invalid request'})@login_required
@user_passes_test(is_admin)
def mentor_assignment_add(request):
    """Add mentor assignment"""
    if request.method == 'POST':
        form = MentorAssignmentForm(request.POST)
        if form.is_valid():
            try:
                assignment = form.save(commit=False)
                assignment.assigned_by = request.user
                assignment.save()
                messages.success(request, 'Mentor assignment added successfully!')
                return redirect('admin_mentor_assignments')  # ✅ Redirect, not JSON
            except Exception as e:
                messages.error(request, f'Error adding assignment: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect('admin_mentor_assignments')
    
    return redirect('admin_mentor_assignments')

@login_required
@user_passes_test(is_admin)
def mentor_assignment_detail(request, pk):
    """Get assignment details for modal"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    
    data = {
        'student': assignment.student.name,
        'register_number': assignment.student.register_number,
        'mentor': assignment.faculty_mentor.user.get_full_name() or assignment.faculty_mentor.user.email,
        'effective_from': assignment.effective_from.strftime('%d %b %Y'),
        'effective_to': assignment.effective_to.strftime('%d %b %Y') if assignment.effective_to else 'Current',
        'level': assignment.get_assignment_level_display(),
        'status': 'Active' if assignment.is_active else 'Inactive',
        'reason': assignment.reason_for_change or 'N/A',
        'remarks': assignment.remarks or 'N/A',
        'is_active': assignment.is_active,
    }
    return JsonResponse(data)

import logging
logger = logging.getLogger(__name__)
@login_required
@user_passes_test(is_admin)
def mentor_assignment_edit(request, pk):
    """Edit mentor assignment via AJAX"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    
    logger.info(f"Edit assignment called for pk: {pk}, method: {request.method}")
    
    if request.method == 'POST':
        logger.info(f"POST data: {request.POST}")
        form = MentorAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Mentor assignment updated successfully!')
                logger.info(f"Assignment {pk} updated successfully")
                return JsonResponse({'success': True, 'message': 'Assignment updated successfully!'})
            except Exception as e:
                logger.error(f"Error saving assignment: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})
        else:
            logger.error(f"Form errors: {form.errors}")
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({'success': False, 'errors': errors})
    
    # GET request - return assignment data
    logger.info(f"Returning assignment data for {pk}")
    data = {
        'id': str(assignment.id),
        'student': str(assignment.student.id),
        'faculty_mentor': str(assignment.faculty_mentor.id),
        'effective_from': assignment.effective_from.strftime('%Y-%m-%d'),
        'effective_to': assignment.effective_to.strftime('%Y-%m-%d') if assignment.effective_to else '',
        'assignment_level': assignment.assignment_level,
        'related_semester': assignment.related_semester or '',
        'reason_for_change': assignment.reason_for_change or '',
        'remarks': assignment.remarks or '',
    }
    return JsonResponse(data)


@login_required
@user_passes_test(is_admin)
def mentor_assignment_toggle(request, pk):
    """Toggle assignment active status"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    if not assignment.is_active:
        conflict = MentorAssignment.objects.filter(
            student=assignment.student,
            is_active=True,
        ).exclude(pk=assignment.pk)
        if conflict.exists():
            messages.error(request, 'Cannot activate this assignment because the student already has an active mentor.')
            return redirect('admin_mentor_assignments')
    assignment.is_active = not assignment.is_active
    assignment.save()
    status = "activated" if assignment.is_active else "deactivated"
    messages.success(request, f'Assignment {status} successfully!')
    return redirect('admin_mentor_assignments')


@login_required
@user_passes_test(is_admin)
def mentor_assignment_delete(request, pk):
    """Delete mentor assignment"""
    assignment = get_object_or_404(MentorAssignment, pk=pk)
    assignment.delete()
    messages.success(request, 'Mentor assignment deleted successfully!')
    return redirect('admin_mentor_assignments')


# ============================================
# REPORTS
# ============================================

@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    """Admin reports page"""
    return render(request, 'admin/reports.html', {'active_tab': 'admin_reports'})


@login_required
@user_passes_test(is_admin)
def consolidated_report(request):
    """Consolidated marks report"""
    for student in Student.objects.select_related('programme').all():
        data = calculate_student_consolidated_marks(student)
        ConsolidatedScore.objects.update_or_create(
            student=student,
            calculation_formula=data.get('formula_used', 'Default (Simple Average)'),
            defaults={
                'regular_internship_average': data.get('regular_average') or 0,
                'assessment_internship_score': data.get('assessment_score'),
                'final_consolidated_score': data.get('final_score') or 0,
            }
        )
    scores = ConsolidatedScore.objects.select_related('student').all()
    
    context = {
        'active_tab': 'consolidated',
        'scores': scores,
    }
    return render(request, 'admin/consolidated_report.html', context)


@login_required
@user_passes_test(is_admin)
def export_report(request, report_type):
    """Export report in Excel/PDF format"""
    export_format = request.GET.get('format', 'excel')
    if report_type == 'student':
        data = _student_report_rows()
        headers = ['Register No', 'Name', 'Programme', 'Batch', 'Degree Start', 'Degree End', 'Status', 'Internships', 'Breaks']
        filename = 'student_report'
    elif report_type == 'internship':
        data = _internship_report_rows()
        headers = ['Register No', 'Student', 'Type', 'Number', 'Organisation', 'Start Date', 'End Date', 'Completion', 'Verification', 'Viva Marks']
        filename = 'internship_report'
    elif report_type == 'organisation':
        data = _organisation_report_rows()
        headers = ['Organisation', 'Type', 'Location', 'Area of Work', 'Status', 'Student Count', 'Internship Count']
        filename = 'organisation_report'
    elif report_type == 'mentor':
        data = _mentor_report_rows()
        headers = ['Register No', 'Student', 'Faculty Mentor', 'Effective From', 'Effective To', 'Semester', 'Level', 'Active']
        filename = 'mentor_assignment_report'
    elif report_type == 'break':
        data = _break_report_rows()
        headers = ['Register No', 'Student', 'Break Type', 'Start Date', 'End Date', 'Approved By', 'Overlapping Internships']
        filename = 'break_report'
    else:
        return HttpResponse(f"Unknown report type: {report_type}", status=400)

    if export_format == 'pdf':
        table_rows = [[row.get(header, '') for header in headers] for row in data]
        return generate_pdf_report(f"{report_type.title()} Report", headers, table_rows, filename)
    return generate_excel_report(data, filename, report_type.title())


def _student_report_rows():
    rows = []
    for student in Student.objects.select_related('programme', 'batch').prefetch_related('internships', 'breaks').order_by('register_number'):
        rows.append({
            'Register No': student.register_number,
            'Name': student.name,
            'Programme': student.programme.name if student.programme else '',
            'Batch': student.batch.name if student.batch else '',
            'Degree Start': student.degree_start_date or '',
            'Degree End': student.degree_end_date or '',
            'Status': student.get_status_display(),
            'Internships': student.internships.count(),
            'Breaks': student.breaks.count(),
        })
    return rows


def _internship_report_rows():
    rows = []
    internships = InternshipRecord.objects.select_related('student', 'organisation').prefetch_related('assessment_marks__assessment_component')
    for internship in internships.order_by('student__register_number', 'internship_number'):
        viva = internship.assessment_marks.filter(assessment_component__assessment_type='viva').first()
        rows.append({
            'Register No': internship.student.register_number,
            'Student': internship.student.name,
            'Type': internship.get_internship_type_display(),
            'Number': internship.internship_number,
            'Organisation': internship.organisation.name,
            'Start Date': internship.start_date,
            'End Date': internship.end_date,
            'Completion': internship.get_completion_status_display(),
            'Verification': internship.get_verification_status_display(),
            'Viva Marks': viva.marks_awarded if viva else 'Pending',
        })
    return rows


def _organisation_report_rows():
    rows = []
    for organisation in Organisation.objects.prefetch_related('internships__student').order_by('name'):
        students = {internship.student_id for internship in organisation.internships.all()}
        rows.append({
            'Organisation': organisation.name,
            'Type': organisation.type_display,
            'Location': ', '.join(filter(None, [organisation.city, organisation.state])),
            'Area of Work': organisation.area_of_work,
            'Status': 'Active' if organisation.is_active else 'Inactive',
            'Student Count': len(students),
            'Internship Count': organisation.internships.count(),
        })
    return rows


def _break_report_rows():
    rows = []
    for break_record in BreakRecord.objects.select_related('student', 'approved_by').order_by('-start_date'):
        overlaps = _break_overlapping_internships(break_record)
        rows.append({
            'Register No': break_record.student.register_number,
            'Student': break_record.student.name,
            'Break Type': break_record.get_break_type_display(),
            'Start Date': break_record.start_date,
            'End Date': break_record.end_date,
            'Approved By': break_record.approved_by.get_full_name() or break_record.approved_by.email if break_record.approved_by else '',
            'Overlapping Internships': len(overlaps),
        })
    return rows


def _mentor_report_rows():
    rows = []
    assignments = MentorAssignment.objects.select_related('student', 'faculty_mentor__user').order_by(
        'student__register_number', '-effective_from'
    )
    for assignment in assignments:
        mentor_user = assignment.faculty_mentor.user
        rows.append({
            'Register No': assignment.student.register_number,
            'Student': assignment.student.name,
            'Faculty Mentor': mentor_user.get_full_name() or mentor_user.email,
            'Effective From': assignment.effective_from,
            'Effective To': assignment.effective_to or '',
            'Semester': assignment.related_semester,
            'Level': assignment.get_assignment_level_display(),
            'Active': 'Yes' if assignment.is_active else 'No',
        })
    return rows


































































































# # Internship-Management-System\apps\core\admin_views.py
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages
# from django.contrib.auth.models import User
# from django.contrib.auth.decorators import login_required
# from django.db.models import Q, Count
# from django.http import JsonResponse, HttpResponse
# from django.template.loader import render_to_string
# from django.core.paginator import Paginator
# import json
# import csv
# from datetime import datetime

# from ..authentication.models import UserProfile
# from .models import (
#     Programme, Batch, Student, Organisation, 
#     InternshipRecord, BreakRecord,
#     MentorAssignment, AssessmentComponent, AssessmentMarks, ConsolidatedScore
# )
# from .decorators import admin_required
# from .forms import (
#     UserForm, StudentForm, OrganisationForm, InternshipForm, 
#     BreakForm, MentorAssignmentForm, AssessmentMarksForm,
#     AssessmentComponentForm, ProgrammeForm, BatchForm, ProfileForm
# )


# # ============================================
# # ADMIN DASHBOARD
# # ============================================

# @admin_required
# def admin_dashboard(request):
#     """Admin Dashboard with statistics"""
#     context = {
#         'total_users': UserProfile.objects.count(),
#         'total_students': Student.objects.count(),
#         'total_organisations': Organisation.objects.count(),
#         'total_internships': InternshipRecord.objects.count(),
#         'pending_verifications': InternshipRecord.objects.filter(verification_status='submitted').count(),
#         'pending_marks': InternshipRecord.objects.filter(verification_status='verified', assessment_marks__isnull=True).count(),
#         'pending_approvals': InternshipRecord.objects.filter(verification_status='verified', completion_status='pending').count(),
#         'active_tab': 'admin_dashboard'
#     }
#     return render(request, 'admin/dashboard.html', context)


# # ============================================
# # USER MANAGEMENT (like teacher_list.html)
# # ============================================

# @admin_required
# def user_list(request):
#     """List all users with filtering"""
#     users = UserProfile.objects.all().select_related('user')
    
#     # Filter by role
#     role_filter = request.GET.get('role')
#     if role_filter:
#         users = users.filter(role=role_filter)
    
#     # Search
#     search = request.GET.get('search')
#     if search:
#         users = users.filter(
#             Q(user__email__icontains=search) |
#             Q(user__first_name__icontains=search) |
#             Q(user__last_name__icontains=search)
#         )
    
#     context = {
#         'users': users,
#         'roles': UserProfile.ROLE_CHOICES,
#         'active_tab': 'admin_users'
#     }
#     return render(request, 'admin/users.html', context)


# @admin_required
# def user_add(request):
#     """Add new user with role"""
#     if request.method == 'POST':
#         form = UserForm(request.POST)
#         if form.is_valid():
#             try:
#                 user = form.save()
#                 messages.success(request, f'User {user.email} created successfully!')
#                 return redirect('admin_users')
#             except Exception as e:
#                 messages.error(request, f'Error creating user: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_users')
    
#     # For GET requests, redirect back (form is in the modal)
#     return redirect('admin_users')


# @admin_required
# def user_edit(request, pk):
#     """Edit user details and role"""
#     profile = get_object_or_404(UserProfile, pk=pk)
#     user = profile.user
    
#     if request.method == 'POST':
#         form = UserForm(request.POST, instance=user)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, f'User {user.email} updated successfully!')
#                 return redirect('admin_users')
#             except Exception as e:
#                 messages.error(request, f'Error updating user: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_users')
    
#     # GET request - render form HTML for modal
#     form = UserForm(instance=user)
#     form.fields['role'].initial = profile.role
#     form.fields['phone_number'].initial = profile.phone_number
#     form.fields['is_active'].initial = profile.is_active
#     return render(request, 'admin/user_form_modal_content.html', {'form': form, 'edit': True, 'profile': profile})


# @admin_required
# def user_toggle(request, pk):
#     """Toggle user active status"""
#     profile = get_object_or_404(UserProfile, pk=pk)
#     if request.method in ['GET', 'POST']:
#         profile.is_active = not profile.is_active
#         profile.save()
#         status = 'activated' if profile.is_active else 'deactivated'
#         messages.success(request, f'User {profile.user.email} {status} successfully!')
#         return redirect('admin_users')
#     return redirect('admin_users')


# @admin_required
# def user_approve(request, pk):
#     """Approve a user (for students)"""
#     profile = get_object_or_404(UserProfile, pk=pk)
#     if request.method in ['GET', 'POST']:
#         profile.is_approved = True
#         profile.save()
#         messages.success(request, f'User {profile.user.email} approved successfully!')
#         return redirect('admin_users')
#     return redirect('admin_users')


# @admin_required
# def user_delete(request, pk):
#     """Delete user (soft delete)"""
#     profile = get_object_or_404(UserProfile, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             profile.is_active = False
#             profile.save()
#             messages.success(request, f'User {profile.user.email} deactivated successfully!')
#         except Exception as e:
#             messages.error(request, f'Error deleting user: {str(e)}')
#         return redirect('admin_users')
#     return redirect('admin_users')


# @admin_required
# def bulk_upload_users(request):
#     """Bulk upload users via CSV"""
#     if request.method == 'POST':
#         uploaded_file = request.FILES.get('csv_file')
#         if not uploaded_file:
#             messages.error(request, 'Please select a CSV file')
#             return redirect('admin_users')
        
#         if not uploaded_file.name.endswith('.csv'):
#             messages.error(request, 'Please upload a CSV file')
#             return redirect('admin_users')
        
#         try:
#             decoded = uploaded_file.read().decode('utf-8-sig')
#             csv_reader = csv.DictReader(decoded.splitlines())
            
#             created_count = 0
#             failed_rows = []
            
#             for row_num, row in enumerate(csv_reader, 2):
#                 try:
#                     email = row.get('EMAIL', '').strip().lower()
#                     if not email:
#                         raise ValueError("Email is required")
                    
#                     if User.objects.filter(email=email).exists():
#                         raise ValueError(f"Email {email} already exists")
                    
#                     password = User.objects.make_random_password()
                    
#                     user = User.objects.create_user(
#                         username=email,
#                         email=email,
#                         first_name=row.get('FIRST_NAME', '').strip(),
#                         last_name=row.get('LAST_NAME', '').strip(),
#                         password=password,
#                         is_staff=True
#                     )
                    
#                     role = row.get('ROLE', 'student').upper()
#                     if role not in ['ADMIN', 'DEPT_ADMIN', 'FACULTY_MENTOR', 'EVALUATOR', 'HOD', 'STUDENT']:
#                         role = 'STUDENT'
                    
#                     UserProfile.objects.create(
#                         user=user,
#                         role=role.lower(),
#                         phone_number=row.get('PHONE', '').strip(),
#                         is_active=True,
#                         is_approved=True
#                     )
                    
#                     created_count += 1
                    
#                 except Exception as e:
#                     failed_rows.append({'row': row_num, 'error': str(e)})
            
#             if created_count > 0:
#                 messages.success(request, f'Successfully created {created_count} user(s)')
            
#             if failed_rows:
#                 messages.warning(request, f'Failed to create {len(failed_rows)} user(s)')
            
#         except Exception as e:
#             messages.error(request, f'Error processing file: {str(e)}')
        
#         return redirect('admin_users')
    
#     return redirect('admin_users')


# # ============================================
# # STUDENT MANAGEMENT
# # ============================================

# @admin_required
# def student_list(request):
#     """List all students with filtering"""
#     students = Student.objects.all().select_related('programme', 'batch')
    
#     # Filters
#     programme = request.GET.get('programme')
#     if programme:
#         students = students.filter(programme_id=programme)
    
#     batch = request.GET.get('batch')
#     if batch:
#         students = students.filter(batch_id=batch)
    
#     status = request.GET.get('status')
#     if status:
#         students = students.filter(status=status)
    
#     search = request.GET.get('search')
#     if search:
#         students = students.filter(
#             Q(name__icontains=search) |
#             Q(register_number__icontains=search) |
#             Q(email__icontains=search)
#         )
    
#     context = {
#         'students': students,
#         'programmes': Programme.objects.filter(is_active=True),
#         'batches': Batch.objects.filter(is_active=True),
#         'status_choices': Student.STATUS_CHOICES,
#         'active_tab': 'admin_students'
#     }
#     return render(request, 'admin/students.html', context)


# @admin_required
# def student_add(request):
#     """Add new student"""
#     if request.method == 'POST':
#         form = StudentForm(request.POST)
#         if form.is_valid():
#             try:
#                 # Save the student - this will create user and profile
#                 student = form.save()
#                 messages.success(request, f'Student {student.name} added successfully!')
#                 return redirect('admin_students')
#             except Exception as e:
#                 # Log the full error for debugging
#                 import traceback
#                 print(f"Error adding student: {str(e)}")
#                 print(traceback.format_exc())
#                 messages.error(request, f'Error adding student: {str(e)}')
#         else:
#             # Form validation errors
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_students')
    
#     return redirect('admin_students')


# @admin_required
# def student_edit(request, pk):
#     """Edit student details"""
#     student = get_object_or_404(Student, pk=pk)
    
#     if request.method == 'POST':
#         form = StudentForm(request.POST, instance=student)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, f'Student {student.name} updated successfully!')
#                 return redirect('admin_students')
#             except Exception as e:
#                 import traceback
#                 print(f"Error updating student: {str(e)}")
#                 print(traceback.format_exc())
#                 messages.error(request, f'Error updating student: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_students')
    
#     return redirect('admin_students')

# @admin_required
# def student_detail(request, pk):
#     """Get student details for modal"""
#     student = get_object_or_404(Student, pk=pk)
#     internships = InternshipRecord.objects.filter(student=student)
    
#     data = {
#         'id': str(student.id),
#         'register_number': student.register_number,
#         'name': student.name,
#         'email': student.email,
#         'mobile': student.mobile or '-',
#         'programme': student.programme.name,
#         'batch': student.batch.name,
#         'degree_start_date': student.degree_start_date.strftime('%d %b %Y'),
#         'degree_end_date': student.degree_end_date.strftime('%d %b %Y') if student.degree_end_date else '-',
#         'status': student.get_status_display(),
#         'internships': [
#             {
#                 'number': i.internship_number,
#                 'organisation': i.organisation.name,
#                 'type': i.get_internship_type_display(),
#                 'start_date': i.start_date.strftime('%d %b %Y'),
#                 'end_date': i.end_date.strftime('%d %b %Y'),
#                 'status': i.get_completion_status_display()
#             } for i in internships
#         ]
#     }
#     return JsonResponse(data)


# @admin_required
# def student_delete(request, pk):
#     """Delete student (soft delete)"""
#     student = get_object_or_404(Student, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             student.status = 'discontinued'
#             student.save()
#             messages.success(request, f'Student {student.name} marked as discontinued!')
#         except Exception as e:
#             messages.error(request, f'Error deleting student: {str(e)}')
#         return redirect('admin_students')
#     return redirect('admin_students')


# # ============================================
# # ORGANISATION MANAGEMENT
# # ============================================

# @admin_required
# def organisation_list(request):
#     """List all organisations with filtering"""
#     organisations = Organisation.objects.all()
    
#     org_type = request.GET.get('type')
#     if org_type:
#         organisations = organisations.filter(organisation_type=org_type)
    
#     search = request.GET.get('search')
#     if search:
#         organisations = organisations.filter(
#             Q(name__icontains=search) |
#             Q(city__icontains=search) |
#             Q(contact_person__icontains=search)
#         )
    
#     context = {
#         'organisations': organisations,
#         'types': Organisation.TYPE_CHOICES,
#         'active_tab': 'admin_organisations'
#     }
#     return render(request, 'admin/organisations.html', context)


# @admin_required
# def organisation_add(request):
#     """Add new organisation"""
#     if request.method == 'POST':
#         form = OrganisationForm(request.POST)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, 'Organisation added successfully!')
#                 return redirect('admin_organisations')
#             except Exception as e:
#                 messages.error(request, f'Error adding organisation: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_organisations')
    
#     form = OrganisationForm()
#     return render(request, 'admin/organisation_form_modal_content.html', {'form': form})


# @admin_required
# def organisation_edit(request, pk):
#     """Edit organisation details"""
#     organisation = get_object_or_404(Organisation, pk=pk)
    
#     if request.method == 'POST':
#         form = OrganisationForm(request.POST, instance=organisation)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, f'Organisation {organisation.name} updated successfully!')
#                 return redirect('admin_organisations')
#             except Exception as e:
#                 messages.error(request, f'Error updating organisation: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_organisations')
    
#     form = OrganisationForm(instance=organisation)
#     return render(request, 'admin/organisation_form_modal_content.html', {'form': form, 'edit': True, 'organisation': organisation})


# @admin_required
# def organisation_toggle(request, pk):
#     """Toggle organisation active status"""
#     organisation = get_object_or_404(Organisation, pk=pk)
#     if request.method in ['GET', 'POST']:
#         organisation.is_active = not organisation.is_active
#         organisation.save()
#         status = 'activated' if organisation.is_active else 'deactivated'
#         messages.success(request, f'Organisation {organisation.name} {status} successfully!')
#         return redirect('admin_organisations')
#     return redirect('admin_organisations')


# @admin_required
# def organisation_delete(request, pk):
#     """Delete organisation (soft delete)"""
#     organisation = get_object_or_404(Organisation, pk=pk)
#     if request.method in ['GET', 'POST']:
#         organisation.is_active = False
#         organisation.save()
#         messages.success(request, f'Organisation {organisation.name} deactivated successfully!')
#         return redirect('admin_organisations')
#     return redirect('admin_organisations')


# # ============================================
# # PROGRAMME MANAGEMENT (like manage_subjects.html)
# # ============================================

# @admin_required
# def programme_list(request):
#     """List all programmes"""
#     programmes = Programme.objects.all()
    
#     context = {
#         'programmes': programmes,
#         'active_tab': 'admin_programmes'
#     }
#     return render(request, 'admin/programmes.html', context)


# @admin_required
# def programme_add(request):
#     """Add new programme"""
#     if request.method == 'POST':
#         form = ProgrammeForm(request.POST)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, 'Programme added successfully!')
#                 return redirect('admin_programmes')
#             except Exception as e:
#                 messages.error(request, f'Error adding programme: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_programmes')
    
#     form = ProgrammeForm()
#     return render(request, 'admin/programme_form_modal_content.html', {'form': form})


# @admin_required
# def programme_edit(request, pk):
#     """Edit programme"""
#     programme = get_object_or_404(Programme, pk=pk)
    
#     if request.method == 'POST':
#         form = ProgrammeForm(request.POST, instance=programme)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, f'Programme {programme.name} updated successfully!')
#                 return redirect('admin_programmes')
#             except Exception as e:
#                 messages.error(request, f'Error updating programme: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_programmes')
    
#     form = ProgrammeForm(instance=programme)
#     return render(request, 'admin/programme_form_modal_content.html', {'form': form, 'edit': True, 'programme': programme})


# @admin_required
# def programme_toggle(request, pk):
#     """Toggle programme active status"""
#     programme = get_object_or_404(Programme, pk=pk)
#     if request.method in ['GET', 'POST']:
#         programme.is_active = not programme.is_active
#         programme.save()
#         status = 'activated' if programme.is_active else 'deactivated'
#         messages.success(request, f'Programme {programme.name} {status} successfully!')
#         return redirect('admin_programmes')
#     return redirect('admin_programmes')


# @admin_required
# def programme_delete(request, pk):
#     """Delete programme"""
#     programme = get_object_or_404(Programme, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             programme.delete()
#             messages.success(request, f'Programme {programme.name} deleted successfully!')
#         except Exception as e:
#             messages.error(request, f'Error deleting programme: {str(e)}')
#         return redirect('admin_programmes')
#     return redirect('admin_programmes')


# # ============================================
# # BATCH MANAGEMENT
# # ============================================

# @admin_required
# def batch_list(request):
#     """List all batches"""
#     batches = Batch.objects.all().select_related('programme')
    
#     context = {
#         'batches': batches,
#         'programmes': Programme.objects.filter(is_active=True),
#         'active_tab': 'admin_batches'
#     }
#     return render(request, 'admin/batches.html', context)


# @admin_required
# def batch_add(request):
#     """Add new batch"""
#     if request.method == 'POST':
#         form = BatchForm(request.POST)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, 'Batch added successfully!')
#                 return redirect('admin_batches')
#             except Exception as e:
#                 messages.error(request, f'Error adding batch: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_batches')
    
#     form = BatchForm()
#     return render(request, 'admin/batch_form_modal_content.html', {'form': form})


# @admin_required
# def batch_edit(request, pk):
#     """Edit batch"""
#     batch = get_object_or_404(Batch, pk=pk)
    
#     if request.method == 'POST':
#         form = BatchForm(request.POST, instance=batch)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, f'Batch {batch.name} updated successfully!')
#                 return redirect('admin_batches')
#             except Exception as e:
#                 messages.error(request, f'Error updating batch: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_batches')
    
#     form = BatchForm(instance=batch)
#     return render(request, 'admin/batch_form_modal_content.html', {'form': form, 'edit': True, 'batch': batch})


# @admin_required
# def batch_toggle(request, pk):
#     """Toggle batch active status"""
#     batch = get_object_or_404(Batch, pk=pk)
#     if request.method in ['GET', 'POST']:
#         batch.is_active = not batch.is_active
#         batch.save()
#         status = 'activated' if batch.is_active else 'deactivated'
#         messages.success(request, f'Batch {batch.name} {status} successfully!')
#         return redirect('admin_batches')
#     return redirect('admin_batches')


# @admin_required
# def batch_delete(request, pk):
#     """Delete batch"""
#     batch = get_object_or_404(Batch, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             batch.delete()
#             messages.success(request, f'Batch {batch.name} deleted successfully!')
#         except Exception as e:
#             messages.error(request, f'Error deleting batch: {str(e)}')
#         return redirect('admin_batches')
#     return redirect('admin_batches')


# # ============================================
# # INTERNSHIP MANAGEMENT
# # ============================================

# @admin_required
# def internship_list(request):
#     """List all internships with filtering"""
#     internships = InternshipRecord.objects.all().select_related('student', 'organisation')
    
#     # Filters
#     internship_type = request.GET.get('type')
#     if internship_type:
#         internships = internships.filter(internship_type=internship_type)
    
#     verification_status = request.GET.get('verification')
#     if verification_status:
#         internships = internships.filter(verification_status=verification_status)
    
#     student = request.GET.get('student')
#     if student:
#         internships = internships.filter(student_id=student)
    
#     context = {
#         'internships': internships,
#         'types': InternshipRecord.INTERNSHIP_TYPES,
#         'verification_statuses': InternshipRecord.VERIFICATION_STATUS,
#         'students': Student.objects.all(),
#         'active_tab': 'admin_internships'
#     }
#     return render(request, 'admin/internships.html', context)


# @admin_required
# def internship_detail(request, pk):
#     """View internship details with marks"""
#     internship = get_object_or_404(InternshipRecord, pk=pk)
#     marks = AssessmentMarks.objects.filter(internship_record=internship).select_related('assessment_component')
    
#     data = {
#         'student': internship.student.name,
#         'register_number': internship.student.register_number,
#         'internship_number': internship.internship_number,
#         'type': internship.get_internship_type_display(),
#         'organisation': internship.organisation.name,
#         'start_date': internship.start_date.strftime('%d %b %Y'),
#         'end_date': internship.end_date.strftime('%d %b %Y'),
#         'duration': internship.duration,
#         'mode': internship.get_mode_display(),
#         'completion_status': internship.get_completion_status_display(),
#         'verification_status': internship.get_verification_status_display(),
#         'nature_of_work': internship.nature_of_work or '-',
#         'marks': [
#             {
#                 'component': m.assessment_component.name,
#                 'max_marks': float(m.maximum_marks),
#                 'marks_awarded': float(m.marks_awarded),
#                 'status': m.get_status_display()
#             } for m in marks
#         ]
#     }
#     return JsonResponse(data)


# # ============================================
# # BREAK MANAGEMENT
# # ============================================

# @admin_required
# def break_list(request):
#     """List all breaks"""
#     breaks = BreakRecord.objects.all().select_related('student')
    
#     context = {
#         'breaks': breaks,
#         'active_tab': 'admin_breaks'
#     }
#     return render(request, 'admin/breaks.html', context)


# @admin_required
# def break_add(request):
#     """Add new break record"""
#     if request.method == 'POST':
#         form = BreakForm(request.POST, request.FILES)
#         if form.is_valid():
#             try:
#                 break_record = form.save(commit=False)
#                 break_record.save()
#                 messages.success(request, 'Break record added successfully!')
#                 return redirect('admin_breaks')
#             except Exception as e:
#                 messages.error(request, f'Error adding break: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_breaks')
    
#     form = BreakForm()
#     return render(request, 'admin/break_form_modal_content.html', {'form': form})


# @admin_required
# def break_edit(request, pk):
#     """Edit break record"""
#     break_record = get_object_or_404(BreakRecord, pk=pk)
    
#     if request.method == 'POST':
#         form = BreakForm(request.POST, request.FILES, instance=break_record)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, 'Break record updated successfully!')
#                 return redirect('admin_breaks')
#             except Exception as e:
#                 messages.error(request, f'Error updating break: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_breaks')
    
#     form = BreakForm(instance=break_record)
#     return render(request, 'admin/break_form_modal_content.html', {'form': form, 'edit': True, 'break_record': break_record})


# @admin_required
# def break_delete(request, pk):
#     """Delete break record"""
#     break_record = get_object_or_404(BreakRecord, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             break_record.delete()
#             messages.success(request, 'Break record deleted successfully!')
#         except Exception as e:
#             messages.error(request, f'Error deleting break: {str(e)}')
#         return redirect('admin_breaks')
#     return redirect('admin_breaks')


# # ============================================
# # ASSESSMENT CONFIGURATION
# # ============================================

# @admin_required
# def assessment_config(request):
#     """Configure assessment components"""
#     components = AssessmentComponent.objects.all()
    
#     if request.method == 'POST':
#         form = AssessmentComponentForm(request.POST)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, 'Assessment component added successfully!')
#                 return redirect('admin_assessment_config')
#             except Exception as e:
#                 messages.error(request, f'Error adding component: {str(e)}')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f'{field}: {error}')
#         return redirect('admin_assessment_config')
    
#     form = AssessmentComponentForm()
#     context = {
#         'components': components,
#         'form': form,
#         'active_tab': 'admin_assessment_config'
#     }
#     return render(request, 'admin/assessment_config.html', context)


# @admin_required
# def assessment_component_delete(request, pk):
#     """Delete assessment component"""
#     component = get_object_or_404(AssessmentComponent, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             component.is_active = False
#             component.save()
#             messages.success(request, f'Component {component.name} deactivated successfully!')
#         except Exception as e:
#             messages.error(request, f'Error deleting component: {str(e)}')
#         return redirect('admin_assessment_config')
#     return redirect('admin_assessment_config')


# # ============================================
# # MENTOR ASSIGNMENT (like assign_teacher_subjects.html)
# # ============================================

# @admin_required
# def mentor_assignment_list(request):
#     """List all mentor assignments"""
#     assignments = MentorAssignment.objects.all().select_related('student', 'faculty_mentor')
    
#     # Get all faculty mentors (users with faculty_mentor role)
#     faculty_mentors = UserProfile.objects.filter(role='faculty_mentor')
    
#     context = {
#         'assignments': assignments,
#         'faculty_mentors': faculty_mentors,
#         'students': Student.objects.all(),
#         'active_tab': 'admin_mentor_assignments'
#     }
#     return render(request, 'admin/mentor_assignments.html', context)


# @admin_required
# def mentor_assignment_add(request):
#     """Add new mentor assignment via AJAX"""
#     if request.method == 'POST':
#         form = MentorAssignmentForm(request.POST)
#         if form.is_valid():
#             try:
#                 assignment = form.save(commit=False)
#                 assignment.assigned_by = request.user
#                 assignment.save()
#                 messages.success(request, 'Mentor assignment added successfully!')
#                 return JsonResponse({'success': True})
#             except Exception as e:
#                 return JsonResponse({'success': False, 'error': str(e)})
#         else:
#             return JsonResponse({'success': False, 'errors': form.errors})
    
#     return JsonResponse({'success': False, 'error': 'Invalid request'})


# @admin_required
# def mentor_assignment_delete(request, pk):
#     """Delete mentor assignment"""
#     assignment = get_object_or_404(MentorAssignment, pk=pk)
#     if request.method in ['GET', 'POST']:
#         try:
#             assignment.delete()
#             messages.success(request, 'Mentor assignment deleted successfully!')
#         except Exception as e:
#             messages.error(request, f'Error deleting assignment: {str(e)}')
#         return redirect('admin_mentor_assignments')
#     return redirect('admin_mentor_assignments')


# # ============================================
# # REPORTS
# # ============================================

# @admin_required
# def admin_reports(request):
#     """Admin Reports page"""
#     return render(request, 'admin/reports.html', {'active_tab': 'admin_reports'})


# @admin_required
# def consolidated_report(request):
#     """Consolidated marks report"""
#     scores = ConsolidatedScore.objects.all().select_related('student')
#     context = {
#         'scores': scores,
#         'active_tab': 'consolidated'
#     }
#     return render(request, 'admin/consolidated_report.html', context)


# @admin_required
# def export_report(request, report_type):
#     """Export report in Excel/PDF format"""
#     # Implementation for export
#     return HttpResponse(f"Exporting {report_type} report...")


# # ============================================
# # ERROR HANDLERS
# # ============================================

# def handler404(request, exception):
#     return render(request, '404.html', status=404)

# def handler403(request, exception):
#     return render(request, '403.html', status=403)

# def handler500(request):
#     return render(request, '500.html', status=500)
