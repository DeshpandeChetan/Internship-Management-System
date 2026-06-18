from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Student, InternshipRecord, MentorAssignment, AssessmentMarks
from .decorators import mentor_required
from ..authentication.models import UserProfile

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
    ).select_related('student')
    return render(request, 'mentor/students.html', {'assignments': assignments, 'active_tab': 'mentor_assigned_students'})

@mentor_required
def student_detail(request, pk):
    """View student details (mentor view)"""
    student = get_object_or_404(Student, pk=pk)
    # Verify this student is assigned to the mentor
    mentor_profile = request.user.profile
    assignment = MentorAssignment.objects.filter(
        student=student,
        faculty_mentor=mentor_profile,
        is_active=True
    ).first()
    
    if not assignment:
        messages.error(request, 'You are not assigned to this student.')
        return redirect('mentor_assigned_students')
    
    internships = InternshipRecord.objects.filter(student=student)
    return render(request, 'mentor/student_detail.html', {
        'student': student,
        'internships': internships,
        'active_tab': 'mentor_assigned_students'
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
    internship = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        internship.verification_status = 'verified'
        internship.verified_by = request.user
        internship.verified_at = datetime.now()
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
    """View internship details (mentor view)"""
    internship = get_object_or_404(InternshipRecord, pk=pk)
    return render(request, 'mentor/internship_detail.html', {'internship': internship})

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