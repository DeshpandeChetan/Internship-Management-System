from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count
from .models import Student, InternshipRecord, MentorAssignment, AssessmentMarks
from .decorators import mentor_required
from .display import user_name_with_role


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
        InternshipRecord.objects.select_related('student', 'organisation', 'created_by', 'updated_by', 'verified_by', 'verified_by__profile'),
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
    internships = InternshipRecord.objects.filter(student__in=students).select_related('student', 'organisation')
    pending_verifications = InternshipRecord.objects.filter(
        student__in=students,
        verification_status='submitted'
    ).count()
    verified_without_marks = internships.filter(verification_status='verified', assessment_marks__isnull=True).count()
    verification_counts = {
        row['verification_status']: row['count']
        for row in internships.values('verification_status').annotate(count=Count('id'))
    }
    completion_counts = {
        row['completion_status']: row['count']
        for row in internships.values('completion_status').annotate(count=Count('id'))
    }
    marks_status_counts = {
        row['assessment_marks__status']: row['count']
        for row in internships.exclude(assessment_marks__status__isnull=True).values('assessment_marks__status').annotate(count=Count('assessment_marks'))
    }
    
    context = {
        'total_students': len(students),
        'total_internships': internships.count(),
        'pending_verifications': pending_verifications,
        'verified_without_marks': verified_without_marks,
        'assignments': assignments,
        'recent_submissions': internships.order_by('-submission_date', '-created_on')[:8],
        'verification_chart': {
            'labels': [label for value, label in InternshipRecord.VERIFICATION_STATUS],
            'data': [verification_counts.get(value, 0) for value, label in InternshipRecord.VERIFICATION_STATUS],
        },
        'completion_chart': {
            'labels': [label for value, label in InternshipRecord.COMPLETION_STATUS],
            'data': [completion_counts.get(value, 0) for value, label in InternshipRecord.COMPLETION_STATUS],
        },
        'marks_status_chart': {
            'labels': [label for value, label in AssessmentMarks.STATUS_CHOICES],
            'data': [marks_status_counts.get(value, 0) for value, label in AssessmentMarks.STATUS_CHOICES],
        },
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
        'programme': student.programme.name if student.programme else '-',
        'batch': student.batch.name if student.batch else '-',
        'degree_period': f"{student.degree_start_date.strftime('%d %b %Y') if student.degree_start_date else '-'} - {student.degree_end_date.strftime('%d %b %Y') if student.degree_end_date else '-'}",
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
        action = request.POST.get('action')
        if action not in ['verified', 'needs_correction', 'rejected']:
            messages.error(request, 'Please choose a valid verification action.')
            return redirect('mentor_verify_internship', pk=internship.pk)

        remarks = request.POST.get('remarks', '').strip()
        if action == 'needs_correction' and not remarks:
            messages.error(request, 'Please mention what changes are required.')
            return redirect(request.META.get('HTTP_REFERER', 'mentor_pending_verification'))

        internship.verification_status = action
        internship.verified_by = request.user
        internship.verified_at = timezone.now()
        if remarks:
            internship.remarks = remarks
        internship.save()
        messages.success(request, f'Internship marked as {internship.get_verification_status_display()}.')
        return redirect(request.META.get('HTTP_REFERER', 'mentor_pending_verification'))
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
    internship = get_assigned_internship_or_404(request, pk)
    if internship.verification_status != 'verified':
        messages.error(request, 'Marks can be entered only after internship verification.')
        return redirect('mentor_all_internships')
    return redirect('evaluator_enter_marks', pk=internship.pk)

@mentor_required
def internship_detail(request, pk):
    """Return assigned internship details for modal."""
    internship = get_assigned_internship_or_404(request, pk)
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
        'verified_by': user_name_with_role(internship.verified_by),
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
