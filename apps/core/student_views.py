from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count
from .models import Student, InternshipRecord, MentorAssignment, AssessmentMarks, Organisation, BreakRecord
from .decorators import student_required
from .forms import InternshipForm, BreakForm
from .display import user_name_with_role
from apps.utils.calculations import calculate_student_consolidated_marks


def get_logged_in_student(request):
    """
    Return the Student record for the logged-in student.

    Some imported/admin-created records can exist with the same email as the
    auth user but without the OneToOne user link. Resolve those by email and
    persist the link so later requests use request.user.student_profile.
    """
    try:
        return request.user.student_profile
    except ObjectDoesNotExist:
        pass

    email = (request.user.email or request.user.username or '').strip()
    if not email:
        return None

    student = Student.objects.filter(email__iexact=email).first()
    if not student:
        return None

    if student.user_id is None:
        student.user = request.user
        student.save(update_fields=['user', 'updated_on'])

    if student.user_id == request.user.id:
        return student

    return None


def require_logged_in_student(request):
    student = get_logged_in_student(request)
    if student:
        return student

    messages.error(request, 'Student profile not found. Please contact administrator.')
    return None


def student_internship_form(*args, student=None, **kwargs):
    form = InternshipForm(*args, student=student, **kwargs)
    form.fields.pop('verification_status', None)
    form.fields.pop('date_override_approved', None)
    form.fields.pop('date_override_reason', None)
    return form


@student_required
def student_dashboard(request):
    """Student Dashboard"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internships = InternshipRecord.objects.filter(student=student)
    verification_counts = {
        row['verification_status']: row['count']
        for row in internships.values('verification_status').annotate(count=Count('id'))
    }
    completion_counts = {
        row['completion_status']: row['count']
        for row in internships.values('completion_status').annotate(count=Count('id'))
    }
    marks = AssessmentMarks.objects.filter(internship_record__student=student)
    marks_by_internship = [
        {
            'label': f'{mark.internship_record.get_internship_type_display()} {mark.internship_record.internship_number}',
            'value': float(mark.marks_awarded),
        }
        for mark in marks.select_related('internship_record', 'assessment_component').order_by('internship_record__internship_number', 'created_on')[:12]
    ]
    
    context = {
        'student': student,
        'total_internships': internships.count(),
        'completed_internships': internships.filter(completion_status='completed').count(),
        'pending_verifications': internships.filter(verification_status='submitted').count(),
        'pending_internships': internships.filter(verification_status='submitted').count(),
        'verified_internships': internships.filter(verification_status='verified').count(),
        'average_marks': marks.aggregate(avg=Avg('marks_awarded'))['avg'],
        'recent_internships': internships.order_by('-created_on')[:5],
        'verification_chart': {
            'labels': [label for value, label in InternshipRecord.VERIFICATION_STATUS],
            'data': [verification_counts.get(value, 0) for value, label in InternshipRecord.VERIFICATION_STATUS],
        },
        'completion_chart': {
            'labels': [label for value, label in InternshipRecord.COMPLETION_STATUS],
            'data': [completion_counts.get(value, 0) for value, label in InternshipRecord.COMPLETION_STATUS],
        },
        'marks_chart': {
            'labels': [item['label'] for item in marks_by_internship],
            'data': [item['value'] for item in marks_by_internship],
        },
        'active_tab': 'student_dashboard'
    }
    return render(request, 'student/dashboard.html', context)

@student_required
def my_internships(request):
    """View student's internships"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internships = InternshipRecord.objects.filter(student=student).select_related('organisation').order_by('-start_date')
    return render(request, 'student/internships.html', {
        'student': student,
        'internships': internships,
        'organisations': Organisation.objects.filter(is_active=True).order_by('name'),
        'internship_types': InternshipRecord.INTERNSHIP_TYPES,
        'completion_statuses': InternshipRecord.COMPLETION_STATUS,
        'verification_statuses': InternshipRecord.VERIFICATION_STATUS,
        'modes': (('offline', 'Offline'), ('online', 'Online'), ('hybrid', 'Hybrid')),
        'active_tab': 'my_internships',
    })

@student_required
def internship_add(request):
    """Add new internship"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    if request.method == 'POST':
        form = student_internship_form(request.POST, request.FILES, student=student)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.student = student
            internship.created_by = request.user
            internship.updated_by = request.user
            internship.verification_status = 'submitted'
            internship.submission_date = internship.submission_date or timezone.now().date()
            internship.save()
            messages.success(request, 'Internship record submitted for faculty verification!')
            return redirect('my_internships')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    return redirect('my_internships')

@student_required
def internship_detail(request, pk):
    """Return internship details for modal"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internship = get_object_or_404(
        InternshipRecord.objects.select_related('organisation', 'created_by', 'updated_by', 'verified_by', 'verified_by__profile'),
        pk=pk,
        student=student
    )
    return JsonResponse({
        'organisation': internship.organisation.name,
        'type': internship.get_internship_type_display(),
        'number': internship.internship_number,
        'academic_phase': internship.academic_phase or '-',
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


@student_required
def internship_edit(request, pk):
    """Edit internship"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internship = get_object_or_404(
        InternshipRecord,
        pk=pk,
        student=student,
        verification_status__in=['draft', 'needs_correction', 'rejected']
    )
    if request.method == 'POST':
        form = student_internship_form(request.POST, request.FILES, instance=internship, student=student)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.verification_status = 'submitted'
            internship.verified_by = None
            internship.verified_at = None
            internship.updated_by = request.user
            internship.submission_date = internship.submission_date or timezone.now().date()
            internship.save()
            messages.success(request, 'Internship updated and submitted for faculty verification!')
            return redirect('my_internships')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    return redirect('my_internships')

@student_required
def internship_delete(request, pk):
    """Delete internship"""
    messages.error(request, 'Students are not allowed to delete internship records.')
    return redirect('my_internships')


@student_required
def internship_toggle(request, pk):
    """Toggle internship active/inactive-style completion status."""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internship = get_object_or_404(InternshipRecord, pk=pk, student=student)
    if internship.completion_status == 'not_completed':
        internship.completion_status = 'pending'
        status = 'activated'
    else:
        internship.completion_status = 'not_completed'
        status = 'deactivated'
    internship.save(update_fields=['completion_status', 'updated_on'])
    messages.success(request, f'Internship {status} successfully!')
    return redirect('my_internships')

@student_required
def my_mentor(request):
    """View assigned mentor"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    assignment = MentorAssignment.objects.filter(
        student=student, 
        is_active=True
    ).first()
    mentor_history = MentorAssignment.objects.filter(student=student).select_related('faculty_mentor__user').order_by('-effective_from')
    return render(request, 'student/mentor.html', {
        'student': student,
        'assignment': assignment,
        'mentor_history': mentor_history,
        'active_tab': 'my_mentor'
    })

@student_required
def my_marks(request):
    """View marks"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internships = InternshipRecord.objects.filter(student=student).select_related('organisation').order_by('internship_number')
    marks_data = []
    for internship in internships:
        viva_marks = AssessmentMarks.objects.filter(
            internship_record=internship,
            assessment_component__assessment_type='viva',
            status__in=['approved', 'locked']
        ).first()
        intermediate_marks = AssessmentMarks.objects.filter(
            internship_record=internship,
            assessment_component__assessment_type='intermediate',
            status__in=['approved', 'locked']
        ).order_by('-assessment_date', '-created_on')
        assessments = AssessmentMarks.objects.filter(
            internship_record=internship,
            status__in=['approved', 'locked']
        ).select_related('assessment_component', 'evaluator').order_by('assessment_date', 'created_on')
        marks_data.append({
            'internship': internship,
            'viva_marks': viva_marks.marks_awarded if viva_marks else None,
            'intermediate_marks': ', '.join(str(mark.marks_awarded) for mark in intermediate_marks) or None,
            'assessments': assessments,
        })

    return render(request, 'student/marks.html', {
        'student': student,
        'marks_data': marks_data,
        'consolidated_data': calculate_student_consolidated_marks(student),
        'active_tab': 'my_marks',
    })


@student_required
def my_breaks(request):
    """View student's break/gap records."""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    breaks = BreakRecord.objects.filter(student=student).select_related('approved_by').order_by('-start_date')
    return render(request, 'student/breaks.html', {
        'student': student,
        'breaks': breaks,
        'active_tab': 'student_breaks',
    })


@student_required
def break_add(request):
    """Allow students to submit their own break/gap record."""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    instance = BreakRecord(student=student)
    if request.method == 'POST':
        form = BreakForm(request.POST, request.FILES, instance=instance)
        form.fields.pop('approved_by', None)
        if form.is_valid():
            break_record = form.save(commit=False)
            break_record.student = student
            break_record.approved_by = None
            break_record.save()
            messages.success(request, 'Break record submitted successfully!')
            return redirect('student_breaks')
    else:
        form = BreakForm(instance=instance)
        form.fields.pop('approved_by', None)

    return render(request, 'student/add_break.html', {
        'student': student,
        'form': form,
        'active_tab': 'student_breaks',
    })

@student_required
def my_achievements(request):
    """View achievements"""
    return render(request, 'student/achievements.html', {'active_tab': 'my_achievements'})

@student_required
def achievement_add(request):
    """Add achievement"""
    if request.method == 'POST':
        messages.success(request, 'Achievement added successfully!')
        return redirect('my_achievements')
    return render(request, 'student/achievement_form.html', {'active_tab': 'my_achievements'})
