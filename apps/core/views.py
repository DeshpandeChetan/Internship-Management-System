# # Internship-Management-System\apps\core\views.py
# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.http import HttpResponse
# from .decorators import role_required  # This should work now

# @login_required
# def dashboard_redirect(request):
#     """Redirect to role-specific dashboard"""
    
#     # Check if user has profile
#     if not hasattr(request.user, 'profile'):
#         messages.error(request, 'User profile not found. Please contact admin.')
#         return redirect('login')
    
#     profile = request.user.profile
    
#     # Check if user is approved
#     if not profile.is_approved:
#         messages.warning(request, 'Your account is pending admin approval. You will be notified when approved.')
#         return render(request, 'accounts/pending_approval.html', {'hide_sidebar': True})
    
#     role = profile.role
    
#     # Role to URL mapping
#     dashboard_urls = {
#         'admin': 'admin_dashboard',
#         'faculty_mentor': 'mentor_dashboard',
#         'evaluator': 'evaluator_dashboard',
#         'hod': 'hod_dashboard',
#         'student': 'student_dashboard',
#     }
    
#     # Get the redirect URL, default to student_dashboard
#     redirect_url = dashboard_urls.get(role, 'student_dashboard')
    
#     try:
#         return redirect(redirect_url)
#     except:
#         # If the named URL doesn't exist, redirect to home
#         messages.error(request, f'Dashboard not found for role: {role}. Please contact admin.')
#         return redirect('home')

# @login_required
# def profile_view(request):
#     """View user profile"""
#     return render(request, 'admin/profile.html', {'active_tab': 'profile'})

# @login_required
# def profile_update(request):
#     """Update user profile via modal"""
#     if request.method == 'POST':
#         user = request.user
#         first_name = request.POST.get('first_name')
#         last_name = request.POST.get('last_name')
#         phone_number = request.POST.get('phone_number')
        
#         if first_name:
#             user.first_name = first_name
#         if last_name:
#             user.last_name = last_name
#         user.save()
        
#         if phone_number:
#             profile = user.profile
#             profile.phone_number = phone_number
#             profile.save()
        
#         messages.success(request, 'Profile updated successfully!')
#         return redirect('profile')
#     return redirect('profile')

# @login_required
# def report_list(request):
#     """List all available reports"""
#     return render(request, 'admin/reports.html', {'active_tab': 'admin_reports'})

# @login_required
# def export_report(request, report_type):
#     """Export report in Excel/PDF format"""
#     return HttpResponse(f"Exporting {report_type} report...")

# def handler404(request, exception):
#     return render(request, '404.html', status=404)

# def handler403(request, exception):
#     return render(request, '403.html', status=403)

# def handler500(request):
#     return render(request, '500.html', status=500)

































# apps/core/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Student, InternshipRecord, AssessmentMarks, MentorAssignment, ConsolidatedScore
from apps.utils.report_generator import generate_excel_report, generate_pdf_report


@login_required
def dashboard_redirect(request):
    """Redirect to role-specific dashboard"""
    
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'User profile not found. Please contact admin.')
        return redirect('login')
    
    profile = request.user.profile
    
    if not profile.is_approved:
        messages.warning(request, 'Your account is pending admin approval.')
        return render(request, 'accounts/pending_approval.html', {'hide_sidebar': True})
    
    role = profile.role
    
    dashboard_urls = {
        'admin': 'admin_dashboard',
        'hod': 'hod_dashboard',  # HOD has its own dashboard
        'faculty_mentor': 'mentor_dashboard',
        'evaluator': 'evaluator_dashboard',
        'student': 'student_dashboard',
    }
    
    redirect_url = dashboard_urls.get(role, 'student_dashboard')
    
    try:
        return redirect(redirect_url)
    except:
        messages.error(request, f'Dashboard not found for role: {role}')
        return redirect('login')


@login_required
def profile_view(request):
    """View user profile"""
    return render(request, 'admin/profile.html', {'active_tab': 'profile'})


@login_required
def profile_update(request):
    """Update user profile via modal"""
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone_number = request.POST.get('phone_number')
        
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        if phone_number is not None and hasattr(request.user, 'profile'):
            profile = request.user.profile
            profile.phone_number = phone_number
            profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return redirect('profile')


@login_required
def report_list(request):
    """List all available reports"""
    role = request.user.profile.role if hasattr(request.user, 'profile') else ''
    active_tab = {
        'admin': 'admin_reports',
        'hod': 'hod_reports',
        'faculty_mentor': 'mentor_reports',
        'evaluator': 'evaluator_reports',
        'student': 'student_reports',
    }.get(role, 'reports')
    return render(request, 'admin/reports.html', {'active_tab': active_tab})


@login_required
def export_report(request, report_type):
    """Export report in Excel/PDF format"""
    role = request.user.profile.role if hasattr(request.user, 'profile') else ''
    export_format = request.GET.get('format', 'excel')

    if role in ['admin', 'hod']:
        from . import admin_views

        report_map = {
            'student': (admin_views._student_report_rows(), ['Register No', 'Name', 'Programme', 'Batch', 'Degree Start', 'Degree End', 'Status', 'Internships', 'Breaks'], 'student_report'),
            'internship': (admin_views._internship_report_rows(), ['Register No', 'Student', 'Type', 'Number', 'Organisation', 'Start Date', 'End Date', 'Completion', 'Verification', 'Viva Marks'], 'internship_report'),
            'organisation': (admin_views._organisation_report_rows(), ['Organisation', 'Type', 'Location', 'Area of Work', 'Status', 'Student Count', 'Internship Count'], 'organisation_report'),
            'mentor': (admin_views._mentor_report_rows(), ['Register No', 'Student', 'Faculty Mentor', 'Effective From', 'Effective To', 'Semester', 'Level', 'Active'], 'mentor_assignment_report'),
            'break': (admin_views._break_report_rows(), ['Register No', 'Student', 'Break Type', 'Start Date', 'End Date', 'Approved By', 'Overlapping Internships'], 'break_report'),
            'consolidated': (_consolidated_report_rows(), ['Register No', 'Student', 'Regular Average', 'Assessment Score', 'Final Score', 'Formula', 'Finalized'], 'consolidated_marks_report'),
        }
    elif role == 'student':
        student = _student_for_user(request.user)
        if not student:
            return HttpResponse("Student profile not found.", status=404)
        report_map = {
            'student': (_student_own_report_rows(student), ['Register No', 'Name', 'Programme', 'Batch', 'Degree Start', 'Degree End', 'Status', 'Internship Count', 'Break Count'], 'my_student_report'),
            'internship': (_student_internship_report_rows(student), ['Type', 'Number', 'Organisation', 'Start Date', 'End Date', 'Completion', 'Verification', 'Viva Marks'], 'my_internship_report'),
        }
    elif role == 'faculty_mentor':
        report_map = {
            'internship': (_mentor_internship_report_rows(request.user), ['Register No', 'Student', 'Type', 'Number', 'Organisation', 'Start Date', 'End Date', 'Completion', 'Verification'], 'mentor_internship_report'),
            'mentor': (_mentor_assignment_report_rows(request.user), ['Register No', 'Student', 'Effective From', 'Effective To', 'Semester', 'Level', 'Active'], 'my_mentor_assignment_report'),
        }
    elif role == 'evaluator':
        report_map = {
            'internship': (_evaluator_marks_report_rows(request.user), ['Register No', 'Student', 'Internship', 'Component', 'Marks', 'Maximum', 'Status', 'Assessment Date'], 'evaluator_marks_report'),
        }
    else:
        return HttpResponse("Reports are not available for this role.", status=403)

    if report_type not in report_map:
        return HttpResponse(f"Unknown report type: {report_type}", status=400)

    data, headers, filename = report_map[report_type]
    if export_format == 'pdf':
        table_rows = [[row.get(header, '') for header in headers] for row in data]
        return generate_pdf_report(f"{report_type.title()} Report", headers, table_rows, filename)
    return generate_excel_report(data, filename, report_type.title())


def _student_for_user(user):
    try:
        return user.student_profile
    except Student.DoesNotExist:
        return Student.objects.filter(email__iexact=user.email).first()


def _student_own_report_rows(student):
    return [{
        'Register No': student.register_number,
        'Name': student.name,
        'Programme': student.programme.name if student.programme else '',
        'Batch': student.batch.name if student.batch else '',
        'Degree Start': student.degree_start_date,
        'Degree End': student.degree_end_date or '',
        'Status': student.get_status_display(),
        'Internship Count': student.internships.count(),
        'Break Count': student.breaks.count(),
    }]


def _student_internship_report_rows(student):
    rows = []
    for internship in student.internships.select_related('organisation').prefetch_related('assessment_marks__assessment_component').order_by('internship_number'):
        viva = internship.assessment_marks.filter(assessment_component__assessment_type='viva').first()
        rows.append({
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


def _mentor_student_ids(user):
    return MentorAssignment.objects.filter(
        faculty_mentor=user.profile,
        is_active=True
    ).values_list('student_id', flat=True)


def _mentor_internship_report_rows(user):
    rows = []
    internships = InternshipRecord.objects.filter(student_id__in=_mentor_student_ids(user)).select_related('student', 'organisation')
    for internship in internships.order_by('student__register_number', 'internship_number'):
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
        })
    return rows


def _mentor_assignment_report_rows(user):
    rows = []
    assignments = MentorAssignment.objects.filter(faculty_mentor=user.profile).select_related('student')
    for assignment in assignments.order_by('student__register_number', '-effective_from'):
        rows.append({
            'Register No': assignment.student.register_number,
            'Student': assignment.student.name,
            'Effective From': assignment.effective_from,
            'Effective To': assignment.effective_to or '',
            'Semester': assignment.related_semester,
            'Level': assignment.get_assignment_level_display(),
            'Active': 'Yes' if assignment.is_active else 'No',
        })
    return rows


def _evaluator_marks_report_rows(user):
    rows = []
    marks = AssessmentMarks.objects.filter(evaluator=user).select_related(
        'internship_record__student', 'assessment_component'
    )
    for mark in marks.order_by('-assessment_date', '-created_on'):
        internship = mark.internship_record
        rows.append({
            'Register No': internship.student.register_number,
            'Student': internship.student.name,
            'Internship': f"{internship.get_internship_type_display()} {internship.internship_number}",
            'Component': mark.assessment_component.name,
            'Marks': mark.marks_awarded,
            'Maximum': mark.maximum_marks,
            'Status': mark.get_status_display(),
            'Assessment Date': mark.assessment_date or '',
        })
    return rows


def _consolidated_report_rows():
    rows = []
    scores = ConsolidatedScore.objects.select_related('student').order_by('student__register_number')
    for score in scores:
        rows.append({
            'Register No': score.student.register_number,
            'Student': score.student.name,
            'Regular Average': score.regular_internship_average or '',
            'Assessment Score': score.assessment_internship_score or '',
            'Final Score': score.final_consolidated_score or '',
            'Formula': score.calculation_formula,
            'Finalized': 'Yes' if score.is_finalized else 'No',
        })
    return rows


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler403(request, exception):
    return render(request, '403.html', status=403)


def handler500(request):
    return render(request, '500.html', status=500)
