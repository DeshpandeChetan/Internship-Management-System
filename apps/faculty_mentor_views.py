# Internship-Management-System\apps\faculty_mentor_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    Student, InternshipRecord, MentorAssignment, AssessmentMarks,
    BreakRecord, Document, Notification, Organisation
)
from .forms import InternshipRecordForm, AssessmentMarksForm, DocumentUploadForm
from .utils.permissions import is_faculty_mentor
from .utils.calculations import calculate_student_consolidated_marks
from .utils.notifications import send_notification


@login_required
@user_passes_test(is_faculty_mentor)
def dashboard(request):
    """Faculty mentor dashboard showing assigned students"""
    # Get all students assigned to this mentor
    mentor_assignments = MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        effective_to__isnull=True
    ).select_related('student')
    
    assigned_students = [assignment.student for assignment in mentor_assignments]
    
    # Statistics
    total_students = len(assigned_students)
    pending_verifications = InternshipRecord.objects.filter(
        student__in=assigned_students,
        verification_status='submitted'
    ).count()
    
    pending_marks = AssessmentMarks.objects.filter(
        internship_record__student__in=assigned_students,
        status='submitted',
        assessment_type='mentor'
    ).count()
    
    completed_internships = InternshipRecord.objects.filter(
        student__in=assigned_students,
        completion_status='completed'
    ).count()
    
    # Recent submissions
    recent_submissions = InternshipRecord.objects.filter(
        student__in=assigned_students,
        verification_status='submitted'
    ).order_by('-updated_at')[:10]
    
    context = {
        'active_tab': 'faculty_mentor_dashboard',
        'total_students': total_students,
        'pending_verifications': pending_verifications,
        'pending_marks': pending_marks,
        'completed_internships': completed_internships,
        'recent_submissions': recent_submissions,
        'assigned_students': assigned_students[:10],
    }
    return render(request, 'faculty_mentor/dashboard.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def assigned_students(request):
    """List all students assigned to this mentor"""
    mentor_assignments = MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        effective_to__isnull=True
    ).select_related('student__programme', 'student__batch')
    
    students = [assignment.student for assignment in mentor_assignments]
    
    # Filters
    programme = request.GET.get('programme')
    batch = request.GET.get('batch')
    search = request.GET.get('search')
    
    if programme:
        students = [s for s in students if s.programme_id == int(programme)]
    if batch:
        students = [s for s in students if s.batch_id == int(batch)]
    if search:
        students = [s for s in students if search.lower() in s.name.lower() or search.lower() in s.register_number.lower()]
    
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'faculty_mentor_students',
        'students': page_obj,
        'total_count': len(students),
    }
    return render(request, 'faculty_mentor/assigned_students.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def student_internships(request, student_id):
    """View all internships of a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Verify this student is assigned to the mentor
    if not MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        student=student,
        effective_to__isnull=True
    ).exists():
        messages.error(request, 'You are not authorized to view this student\'s records.')
        return redirect('faculty_mentor_assigned_students')
    
    internships = student.internship_records.all().order_by('internship_number')
    
    context = {
        'active_tab': 'faculty_mentor_students',
        'student': student,
        'internships': internships,
    }
    return render(request, 'faculty_mentor/student_internships.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def verify_internship(request, internship_id):
    """Verify internship details submitted by student"""
    internship = get_object_or_404(InternshipRecord, id=internship_id)
    
    # Verify authorization
    if not MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        student=internship.student,
        effective_to__isnull=True
    ).exists():
        messages.error(request, 'You are not authorized to verify this internship.')
        return redirect('faculty_mentor_assigned_students')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        
        if action == 'verify':
            internship.verification_status = 'verified'
            internship.verified_by = request.user
            internship.verified_at = timezone.now()
            internship.remarks = remarks
            internship.save()
            
            # Send notification to student
            if internship.student.user:
                send_notification(
                    recipient=internship.student.user,
                    title='Internship Verified',
                    message=f'Your internship at {internship.organisation.name} has been verified.',
                    notification_type='success'
                )
            messages.success(request, 'Internship verified successfully!')
            
        elif action == 'reject':
            internship.verification_status = 'rejected'
            internship.remarks = remarks
            internship.save()
            
            if internship.student.user:
                send_notification(
                    recipient=internship.student.user,
                    title='Internship Rejected',
                    message=f'Your internship at {internship.organisation.name} needs correction. Reason: {remarks}',
                    notification_type='error'
                )
            messages.warning(request, 'Internship rejected with remarks.')
            
        elif action == 'needs_correction':
            internship.verification_status = 'needs_correction'
            internship.remarks = remarks
            internship.save()
            
            if internship.student.user:
                send_notification(
                    recipient=internship.student.user,
                    title='Internship Needs Correction',
                    message=f'Please correct your internship details for {internship.organisation.name}. Remarks: {remarks}',
                    notification_type='warning'
                )
            messages.info(request, 'Internship marked for correction.')
        
        return redirect('faculty_mentor_student_internships', student_id=internship.student.id)
    
    context = {
        'internship': internship,
        'student': internship.student,
    }
    return render(request, 'faculty_mentor/verify_internship.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def enter_mentor_marks(request, internship_id):
    """Enter mentor evaluation marks for internship"""
    internship = get_object_or_404(InternshipRecord, id=internship_id)
    
    # Verify authorization
    if not MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        student=internship.student,
        effective_to__isnull=True
    ).exists():
        messages.error(request, 'You are not authorized to enter marks for this student.')
        return redirect('faculty_mentor_assigned_students')
    
    # Get or create mentor assessment entry
    mentor_assessment, created = AssessmentMarks.objects.get_or_create(
        internship_record=internship,
        assessment_type='mentor',
        assessment_name='Mentor Evaluation',
        defaults={
            'maximum_marks': 100,
            'evaluator': request.user,
        }
    )
    
    if request.method == 'POST':
        form = AssessmentMarksForm(request.POST, instance=mentor_assessment)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.evaluator = request.user
            assessment.status = 'submitted'
            assessment.save()
            
            if internship.student.user:
                send_notification(
                    recipient=internship.student.user,
                    title='Mentor Marks Entered',
                    message=f'Mentor evaluation marks for {internship.organisation.name} have been entered.',
                    notification_type='info'
                )
            messages.success(request, 'Mentor marks entered successfully!')
            return redirect('faculty_mentor_student_internships', student_id=internship.student.id)
    else:
        form = AssessmentMarksForm(instance=mentor_assessment)
        form.fields['internship_record'].widget.attrs['readonly'] = True
    
    context = {
        'form': form,
        'internship': internship,
        'student': internship.student,
        'title': 'Enter Mentor Marks',
    }
    return render(request, 'faculty_mentor/enter_marks.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def pending_verifications(request):
    """List all pending internship verifications"""
    # Get all students assigned to this mentor
    mentor_assignments = MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        effective_to__isnull=True
    ).select_related('student')
    
    assigned_students = [assignment.student for assignment in mentor_assignments]
    
    pending_internships = InternshipRecord.objects.filter(
        student__in=assigned_students,
        verification_status='submitted'
    ).select_related('student', 'organisation').order_by('-student_submission_date')
    
    paginator = Paginator(pending_internships, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'faculty_mentor_pending',
        'pending_internships': page_obj,
        'total_count': pending_internships.count(),
    }
    return render(request, 'faculty_mentor/pending_verifications.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def student_progress_report(request, student_id):
    """Generate progress report for a student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Verify authorization
    if not MentorAssignment.objects.filter(
        faculty_mentor=request.user,
        student=student,
        effective_to__isnull=True
    ).exists():
        messages.error(request, 'You are not authorized to view this student\'s report.')
        return redirect('faculty_mentor_assigned_students')
    
    internships = student.internship_records.all().order_by('internship_number')
    breaks = student.breaks.all().order_by('-start_date')
    
    # Calculate consolidated marks
    consolidated_data = calculate_student_consolidated_marks(student)
    
    context = {
        'active_tab': 'faculty_mentor_reports',
        'student': student,
        'internships': internships,
        'breaks': breaks,
        'consolidated_data': consolidated_data,
    }
    return render(request, 'faculty_mentor/student_progress_report.html', context)


@login_required
@user_passes_test(is_faculty_mentor)
def add_mentor_remarks(request, internship_id):
    """Add remarks to internship record"""
    internship = get_object_or_404(InternshipRecord, id=internship_id)
    
    if request.method == 'POST':
        remarks = request.POST.get('remarks')
        internship.remarks = remarks
        internship.save()
        
        messages.success(request, 'Remarks added successfully!')
        return redirect('faculty_mentor_student_internships', student_id=internship.student.id)
    
    context = {
        'internship': internship,
    }
    return render(request, 'faculty_mentor/add_remarks.html', context)