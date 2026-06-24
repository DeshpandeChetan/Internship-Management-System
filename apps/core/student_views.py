from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from .models import Student, InternshipRecord, MentorAssignment, AssessmentMarks, Organisation
from .decorators import student_required
from .forms import InternshipForm


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


@student_required
def student_dashboard(request):
    """Student Dashboard"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internships = InternshipRecord.objects.filter(student=student)
    
    context = {
        'student': student,
        'total_internships': internships.count(),
        'completed_internships': internships.filter(completion_status='completed').count(),
        'pending_verifications': internships.filter(verification_status='submitted').count(),
        'pending_internships': internships.filter(verification_status='submitted').count(),
        'recent_internships': internships.order_by('-created_on')[:5],
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
        form = InternshipForm(request.POST, request.FILES)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.student = student
            internship.created_by = request.user
            internship.verification_status = 'draft'
            internship.save()
            messages.success(request, 'Internship record added successfully!')
            return redirect('my_internships')
    else:
        form = InternshipForm()
    return render(request, 'student/internship_form.html', {'student': student, 'form': form, 'active_tab': 'my_internships'})

@student_required
def internship_detail(request, pk):
    """Return internship details for modal"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internship = get_object_or_404(InternshipRecord.objects.select_related('organisation'), pk=pk, student=student)
    return JsonResponse({
        'organisation': internship.organisation.name,
        'type': internship.get_internship_type_display(),
        'number': internship.internship_number,
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


@student_required
def internship_edit(request, pk):
    """Edit internship"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internship = get_object_or_404(InternshipRecord, pk=pk, student=student)
    if request.method == 'POST':
        form = InternshipForm(request.POST, request.FILES, instance=internship)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.verification_status = 'draft'
            internship.save()
            messages.success(request, 'Internship updated successfully!')
            return redirect('my_internships')
    else:
        form = InternshipForm(instance=internship)
    return render(request, 'student/internship_form.html', {'student': student, 'form': form, 'active_tab': 'my_internships'})

@student_required
def internship_delete(request, pk):
    """Delete internship"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    internship = get_object_or_404(InternshipRecord, pk=pk, student=student)
    if request.method == 'POST':
        internship.delete()
        messages.success(request, 'Internship deleted successfully!')
        return redirect('my_internships')
    return render(request, 'student/internship_confirm_delete.html', {'student': student, 'internship': internship})


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
    return render(request, 'student/mentor.html', {'student': student, 'assignment': assignment, 'active_tab': 'my_mentor'})

@student_required
def my_marks(request):
    """View marks"""
    student = require_logged_in_student(request)
    if not student:
        return redirect('profile')

    marks = AssessmentMarks.objects.filter(
        internship_record__student=student
    ).select_related('internship_record', 'assessment_component')
    return render(request, 'student/marks.html', {'student': student, 'marks': marks, 'active_tab': 'my_marks'})

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
