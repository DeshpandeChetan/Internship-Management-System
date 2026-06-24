from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Student, InternshipRecord, MentorAssignment, AssessmentMarks
from .decorators import mentor_required


def get_assigned_student_ids(request):
    return MentorAssignment.objects.filter(
        faculty_mentor=request.user.profile,
        is_active=True
    ).values_list('student_id', flat=True)


def get_assigned_student_or_404(request, pk):
    return get_object_or_404(
        Student.objects.select_related('programme', 'batch'),
        pk=pk,
        id__in=get_assigned_student_ids(request)
    )


def get_assigned_internship_or_404(request, pk):
    return get_object_or_404(
        InternshipRecord.objects.select_related('student', 'organisation'),
        pk=pk,
        student_id__in=get_assigned_student_ids(request)
    )

@mentor_required
def mentor_dashboard(request):
    """Mentor Dashboard"""
    mentor_profile = request.user.profile
    assignments = MentorAssignment.objects.filter(
        faculty_mentor=mentor_profile,
        is_active=True
    ).select_related('student')
    
    students = [a.student for a in assignments]
    pending_verifications = InternshipRecord.objects.filter(
        student__in=students,
        verification_status='submitted'
    ).count()
    
    context = {
        'total_students': len(students),
        'pending_verifications': pending_verifications,
        'assignments': assignments,
        'active_tab': 'mentor_dashboard'
    }
    return render(request, 'mentor/dashboard.html', context)

@mentor_required
def assigned_students(request):
    """View assigned students"""
    mentor_profile = request.user.profile
    assignments = MentorAssignment.objects.filter(
        faculty_mentor=mentor_profile,
        is_active=True
    ).select_related('student', 'student__programme', 'student__batch')
    rows = []
    for assignment in assignments:
        latest_internship = InternshipRecord.objects.filter(
            student=assignment.student
        ).select_related('organisation').order_by('-start_date', '-created_on').first()
        rows.append({
            'assignment': assignment,
            'latest_internship': latest_internship,
        })
    return render(request, 'mentor/students.html', {
        'rows': rows,
        'active_tab': 'mentor_assigned_students'
    })

@mentor_required
def student_detail(request, pk):
    """Return assigned student details for modal."""
    student = get_assigned_student_or_404(request, pk)
    internships = InternshipRecord.objects.filter(student=student).select_related('organisation').order_by('-start_date')
    assignment = MentorAssignment.objects.filter(
        student=student,
        faculty_mentor=request.user.profile,
        is_active=True
    ).first()

    return JsonResponse({
        'register_number': student.register_number,
        'name': student.name,
        'email': student.email,
        'mobile': student.mobile or '-',
        'programme': student.programme.name,
        'batch': student.batch.name,
        'degree_period': f"{student.degree_start_date.strftime('%d %b %Y')} - {student.degree_end_date.strftime('%d %b %Y') if student.degree_end_date else '-'}",
        'status': student.get_status_display(),
        'mentor_since': assignment.effective_from.strftime('%d %b %Y') if assignment else '-',
        'total_internships': internships.count(),
        'completed_internships': internships.filter(completion_status='completed').count(),
        'pending_verifications': internships.filter(verification_status='submitted').count(),
        'internships': [
            {
                'number': internship.internship_number,
                'type': internship.get_internship_type_display(),
                'organisation': internship.organisation.name,
                'period': f"{internship.start_date.strftime('%d %b %Y')} - {internship.end_date.strftime('%d %b %Y')}",
                'status': internship.get_completion_status_display(),
                'verification': internship.get_verification_status_display(),
            }
            for internship in internships
        ],
    })

@mentor_required
def pending_verification(request):
    """View pending verifications"""
    mentor_profile = request.user.profile
    assignments = MentorAssignment.objects.filter(
        faculty_mentor=mentor_profile,
        is_active=True
    ).values_list('student', flat=True)
    
    internships = InternshipRecord.objects.filter(
        student__in=assignments,
        verification_status='submitted'
    ).select_related('student', 'organisation')
    
    return render(request, 'mentor/pending_verification.html', {
        'internships': internships,
        'active_tab': 'mentor_pending_verification'
    })

@mentor_required
def verify_internship(request, pk):
    """Verify an internship"""
    internship = get_assigned_internship_or_404(request, pk)
    if request.method == 'POST':
        internship.verification_status = 'verified'
        internship.verified_by = request.user
        internship.verified_at = timezone.now()
        internship.save()
        messages.success(request, 'Internship verified successfully!')
        return redirect('mentor_pending_verification')
    return render(request, 'mentor/verify_internship.html', {'internship': internship})

@mentor_required
def add_remark(request, pk):
    """Add remark for student"""
    if request.method == 'POST':
        messages.success(request, 'Remark added successfully!')
        return redirect('mentor_assigned_students')
    return render(request, 'mentor/add_remark.html')

@mentor_required
def enter_marks(request, pk):
    """Enter marks for internship"""
    if request.method == 'POST':
        messages.success(request, 'Marks entered successfully!')
        return redirect('mentor_assigned_students')
    return render(request, 'mentor/enter_marks.html')

@mentor_required
def internship_detail(request, pk):
    """Return assigned internship details for modal."""
    internship = get_assigned_internship_or_404(request, pk)
    return JsonResponse({
        'student': f'{internship.student.name} ({internship.student.register_number})',
        'type': internship.get_internship_type_display(),
        'number': internship.internship_number,
        'organisation': internship.organisation.name,
        'semester': internship.related_semester or '-',
        'period': f"{internship.start_date.strftime('%d %b %Y')} - {internship.end_date.strftime('%d %b %Y')}",
        'duration': f'{internship.duration} days' if internship.duration is not None else '-',
        'mode': internship.get_mode_display(),
        'completion_status': internship.get_completion_status_display(),
        'verification_status': internship.get_verification_status_display(),
        'submission_date': internship.submission_date.strftime('%d %b %Y') if internship.submission_date else '-',
        'nature_of_work': internship.nature_of_work or '-',
        'remarks': internship.remarks or '-',
    })

@mentor_required
def all_internships(request):
    """View all internships (mentor view)"""
    mentor_profile = request.user.profile
    assignments = MentorAssignment.objects.filter(
        faculty_mentor=mentor_profile,
        is_active=True
    ).values_list('student', flat=True)
    
    internships = InternshipRecord.objects.filter(
        student__in=assignments
    ).select_related('student', 'organisation')
    
    return render(request, 'mentor/all_internships.html', {
        'internships': internships,
        'active_tab': 'mentor_all_internships'
    })
