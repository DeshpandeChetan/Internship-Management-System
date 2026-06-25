from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms
from django.http import JsonResponse
from django.utils import timezone
from .models import InternshipRecord, AssessmentMarks, AssessmentComponent, AssessmentMarksHistory, MentorAssignment
from .forms import AssessmentMarksForm
from .decorators import evaluator_required


def _can_access_assessment(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role in [
        'admin', 'hod', 'evaluator', 'faculty_evaluator', 'faculty_mentor'
    ]


def assessment_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _can_access_assessment(request.user):
            messages.error(request, 'Assessment access required.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def _assigned_student_ids(user):
    if not hasattr(user, 'profile'):
        return []
    return MentorAssignment.objects.filter(
        faculty_mentor=user.profile,
        is_active=True
    ).values_list('student_id', flat=True)


def _assessment_internships_for(user):
    internships = InternshipRecord.objects.filter(
        verification_status='verified'
    ).select_related('student', 'organisation').prefetch_related('assessment_marks__assessment_component')

    role = user.profile.role
    if role == 'faculty_mentor':
        internships = internships.filter(student_id__in=_assigned_student_ids(user))
    elif role == 'hod' and user.profile.department_id:
        internships = internships.filter(student__department=user.profile.department)
    return internships


def _marks_for(user):
    marks = AssessmentMarks.objects.select_related(
        'internship_record__student',
        'internship_record__organisation',
        'assessment_component',
        'evaluator',
        'locked_by',
    ).prefetch_related('edit_history__edited_by')

    role = user.profile.role
    if role == 'faculty_mentor':
        marks = marks.filter(internship_record__student_id__in=_assigned_student_ids(user))
    elif role == 'hod' and user.profile.department_id:
        marks = marks.filter(internship_record__student__department=user.profile.department)
    elif role in ['evaluator', 'faculty_evaluator']:
        marks = marks.filter(evaluator=user)
    return marks


def _snapshot(marks):
    return {
        'assessment_component': str(marks.assessment_component_id),
        'assessment_name': marks.assessment_name,
        'maximum_marks': str(marks.maximum_marks),
        'marks_awarded': str(marks.marks_awarded),
        'weightage': str(marks.weightage),
        'assessment_date': marks.assessment_date.isoformat() if marks.assessment_date else '',
        'status': marks.status,
        'remarks': marks.remarks,
    }


def _prepare_marks_form(form, internship=None):
    form.fields['internship_record'].widget = forms.HiddenInput()
    form.fields['assessment_component'].queryset = AssessmentComponent.objects.filter(is_active=True)
    form.fields['assessment_date'].required = True
    if internship:
        form.fields['internship_record'].initial = internship


def _apply_component_defaults(marks):
    component = marks.assessment_component
    if not marks.assessment_name:
        marks.assessment_name = component.name
    if not marks.maximum_marks:
        marks.maximum_marks = component.default_max_marks
    if marks.weightage in [None, Decimal('0')] and component.weightage:
        marks.weightage = component.weightage


@assessment_required
def evaluator_dashboard(request):
    """Evaluator Dashboard"""
    internships = _assessment_internships_for(request.user)
    marks = _marks_for(request.user)
    context = {
        'pending_assessments': internships.count(),
        'total_assessments': marks.count(),
        'active_tab': 'evaluator_dashboard'
    }
    return render(request, 'evaluator/dashboard.html', context)


@assessment_required
def pending_assessments(request):
    """View pending assessments"""
    internships = _assessment_internships_for(request.user).order_by('-submission_date', '-created_on')
    assessment_rows = []
    for internship in internships:
        form = AssessmentMarksForm(initial={
            'internship_record': internship,
            'assessment_date': timezone.now().date()
        })
        _prepare_marks_form(form, internship)
        assessment_rows.append({
            'internship': internship,
            'form': form,
        })

    return render(request, 'evaluator/pending_assessments.html', {
        'assessment_rows': assessment_rows,
        'active_tab': 'evaluator_pending_assessments'
    })


@assessment_required
def enter_marks(request, pk):
    """Enter marks for assessment"""
    internship = get_object_or_404(_assessment_internships_for(request.user), pk=pk)
    if request.method == 'POST':
        form = AssessmentMarksForm(request.POST, request.FILES)
        _prepare_marks_form(form, internship)
        if form.is_valid():
            marks = form.save(commit=False)
            marks.internship_record = internship
            marks.evaluator = request.user
            _apply_component_defaults(marks)
            if marks.status == 'locked':
                marks.locked_by = request.user
                marks.locked_at = timezone.now()
            marks.save()
            messages.success(request, 'Assessment marks saved successfully!')
            return redirect('evaluator_history')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        return redirect('evaluator_pending_assessments')
    form = AssessmentMarksForm(initial={'internship_record': internship, 'assessment_date': timezone.now().date()})
    _prepare_marks_form(form, internship)
    return render(request, 'evaluator/enter_marks.html', {'internship': internship, 'form': form, 'active_tab': 'evaluator_pending_assessments'})


@assessment_required
def edit_marks(request, pk):
    """Edit existing marks"""
    marks = get_object_or_404(_marks_for(request.user), pk=pk)
    if marks.status == 'locked':
        messages.error(request, 'Locked marks cannot be edited.')
        return redirect('evaluator_history')

    if request.method == 'POST':
        old_values = _snapshot(marks)
        form = AssessmentMarksForm(request.POST, request.FILES, instance=marks)
        _prepare_marks_form(form, marks.internship_record)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.evaluator = request.user
            _apply_component_defaults(updated)
            if updated.status == 'locked':
                updated.locked_by = request.user
                updated.locked_at = timezone.now()
            updated.save()
            new_values = _snapshot(updated)
            if old_values != new_values:
                AssessmentMarksHistory.objects.create(
                    assessment_marks=updated,
                    edited_by=request.user,
                    old_values=old_values,
                    new_values=new_values,
                    remarks=request.POST.get('edit_reason', '').strip()
                )
            messages.success(request, 'Marks updated successfully!')
            return redirect('evaluator_history')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    form = AssessmentMarksForm(instance=marks)
    _prepare_marks_form(form, marks.internship_record)
    return render(request, 'evaluator/enter_marks.html', {'marks': marks, 'internship': marks.internship_record, 'form': form, 'active_tab': 'evaluator_history'})


@assessment_required
def lock_marks(request, pk):
    """Lock approved marks to prevent unauthorized changes."""
    marks = get_object_or_404(_marks_for(request.user), pk=pk)
    if request.method != 'POST':
        return redirect('evaluator_history')
    if marks.status != 'approved':
        messages.error(request, 'Only approved marks can be locked.')
        return redirect('evaluator_history')
    old_values = _snapshot(marks)
    marks.status = 'locked'
    marks.locked_by = request.user
    marks.locked_at = timezone.now()
    marks.save(update_fields=['status', 'locked_by', 'locked_at', 'updated_on'])
    AssessmentMarksHistory.objects.create(
        assessment_marks=marks,
        edited_by=request.user,
        old_values=old_values,
        new_values=_snapshot(marks),
        remarks='Marks locked after approval.'
    )
    messages.success(request, 'Marks locked successfully.')
    return redirect('evaluator_history')


@assessment_required
def mark_history(request, pk):
    marks = get_object_or_404(_marks_for(request.user), pk=pk)
    history = [
        {
            'edited_by': item.edited_by.get_full_name() or item.edited_by.email if item.edited_by else '-',
            'edited_on': item.edited_on.strftime('%d %b %Y %I:%M %p'),
            'old_values': item.old_values,
            'new_values': item.new_values,
            'remarks': item.remarks or '-',
        }
        for item in marks.edit_history.all()
    ]
    return JsonResponse({'history': history})


@assessment_required
def assessment_history(request):
    """View assessment history"""
    marks = _marks_for(request.user).order_by('-assessment_date', '-created_on')
    return render(request, 'evaluator/history.html', {
        'marks': marks,
        'active_tab': 'evaluator_history'
    })
