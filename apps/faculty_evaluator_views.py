# faculty_evaluator_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    Student, InternshipRecord, AssessmentMarks, User
)
from .forms import AssessmentMarksForm
from .utils.permissions import is_faculty_evaluator
from .utils.notifications import send_notification


@login_required
@user_passes_test(is_faculty_evaluator)
def dashboard(request):
    """Evaluator dashboard"""
    # Get pending assessments
    pending_assessments = AssessmentMarks.objects.filter(
        status='submitted',
        assessment_type__in=['intermediate', 'viva', 'report', 'presentation']
    ).select_related('internship_record__student', 'internship_record__organisation')
    
    # Get completed assessments by this evaluator
    completed_assessments = AssessmentMarks.objects.filter(
        evaluator=request.user,
        status='approved'
    ).count()
    
    context = {
        'active_tab': 'evaluator_dashboard',
        'pending_assessments': pending_assessments[:10],
        'pending_count': pending_assessments.count(),
        'completed_count': completed_assessments,
        'total_assessed': AssessmentMarks.objects.filter(evaluator=request.user).count(),
    }
    return render(request, 'faculty_evaluator/dashboard.html', context)


@login_required
@user_passes_test(is_faculty_evaluator)
def pending_assessments(request):
    """List all pending assessments for evaluation"""
    pending_assessments = AssessmentMarks.objects.filter(
        status='submitted',
        assessment_type__in=['intermediate', 'viva', 'report', 'presentation']
    ).select_related('internship_record__student', 'internship_record__organisation')
    
    # Filters
    assessment_type = request.GET.get('type')
    if assessment_type:
        pending_assessments = pending_assessments.filter(assessment_type=assessment_type)
    
    paginator = Paginator(pending_assessments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'evaluator_pending',
        'assessments': page_obj,
        'total_count': pending_assessments.count(),
        'assessment_types': AssessmentMarks.ASSESSMENT_TYPE_CHOICES,
    }
    return render(request, 'faculty_evaluator/pending_assessments.html', context)


@login_required
@user_passes_test(is_faculty_evaluator)
def enter_viva_marks(request, internship_id):
    """Enter viva marks for an internship"""
    internship = get_object_or_404(InternshipRecord, id=internship_id)
    
    # Get or create viva assessment
    viva_assessment, created = AssessmentMarks.objects.get_or_create(
        internship_record=internship,
        assessment_type='viva',
        assessment_name='Final Viva Voce',
        defaults={
            'maximum_marks': 100,
            'evaluator': request.user,
            'status': 'draft'
        }
    )
    
    if request.method == 'POST':
        form = AssessmentMarksForm(request.POST, instance=viva_assessment)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.evaluator = request.user
            assessment.status = 'submitted'
            assessment.save()
            
            # Update internship completion status if viva marks are entered
            internship.completion_status = 'completed'
            internship.save()
            
            # Send notification to student
            if internship.student.user:
                send_notification(
                    recipient=internship.student.user,
                    title='Viva Marks Entered',
                    message=f'Your viva marks for {internship.organisation.name} have been entered.',
                    notification_type='success'
                )
            
            messages.success(request, 'Viva marks entered successfully!')
            return redirect('evaluator_dashboard')
    else:
        form = AssessmentMarksForm(instance=viva_assessment)
        form.fields['internship_record'].widget.attrs['readonly'] = True
    
    context = {
        'form': form,
        'internship': internship,
        'student': internship.student,
        'title': 'Enter Viva Marks',
    }
    return render(request, 'faculty_evaluator/enter_marks.html', context)


@login_required
@user_passes_test(is_faculty_evaluator)
def enter_intermediate_marks(request, internship_id):
    """Enter intermediate assessment marks"""
    internship = get_object_or_404(InternshipRecord, id=internship_id)
    
    if request.method == 'POST':
        form = AssessmentMarksForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.internship_record = internship
            assessment.evaluator = request.user
            assessment.status = 'submitted'
            assessment.save()
            
            if internship.student.user:
                send_notification(
                    recipient=internship.student.user,
                    title='Intermediate Marks Entered',
                    message=f'Intermediate marks for {internship.organisation.name} have been entered.',
                    notification_type='info'
                )
            
            messages.success(request, 'Intermediate marks entered successfully!')
            return redirect('evaluator_pending_assessments')
    else:
        form = AssessmentMarksForm()
        form.fields['assessment_type'].initial = 'intermediate'
        form.fields['internship_record'].queryset = InternshipRecord.objects.filter(id=internship_id)
    
    context = {
        'form': form,
        'internship': internship,
        'title': 'Enter Intermediate Marks',
    }
    return render(request, 'faculty_evaluator/enter_marks.html', context)


@login_required
@user_passes_test(is_faculty_evaluator)
def review_assessment(request, assessment_id):
    """Review and approve/reject assessment marks"""
    assessment = get_object_or_404(AssessmentMarks, id=assessment_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        
        if action == 'approve':
            assessment.status = 'approved'
            assessment.remarks = remarks
            assessment.save()
            
            if assessment.internship_record.student.user:
                send_notification(
                    recipient=assessment.internship_record.student.user,
                    title='Marks Approved',
                    message=f'Your {assessment.assessment_name} marks have been approved.',
                    notification_type='success'
                )
            messages.success(request, 'Assessment approved successfully!')
            
        elif action == 'reject':
            assessment.status = 'draft'
            assessment.remarks = remarks
            assessment.save()
            
            if assessment.internship_record.student.user:
                send_notification(
                    recipient=assessment.internship_record.student.user,
                    title='Marks Needs Revision',
                    message=f'Your {assessment.assessment_name} marks need revision. Remarks: {remarks}',
                    notification_type='warning'
                )
            messages.warning(request, 'Assessment rejected with remarks.')
        
        return redirect('evaluator_pending_assessments')
    
    context = {
        'assessment': assessment,
        'internship': assessment.internship_record,
        'student': assessment.internship_record.student,
    }
    return render(request, 'faculty_evaluator/review_assessment.html', context)


@login_required
@user_passes_test(is_faculty_evaluator)
def lock_marks(request, internship_id):
    """Lock marks for an internship (final approval)"""
    internship = get_object_or_404(InternshipRecord, id=internship_id)
    
    if request.method == 'POST':
        # Lock all assessments for this internship
        internship.assessment_marks.update(status='locked')
        
        # Update internship verification status
        internship.verification_status = 'locked'
        internship.save()
        
        if internship.student.user:
            send_notification(
                recipient=internship.student.user,
                title='Marks Locked',
                message=f'Marks for {internship.organisation.name} have been locked and cannot be changed.',
                notification_type='info'
            )
        
        messages.success(request, 'Marks locked successfully!')
        return redirect('evaluator_dashboard')
    
    context = {
        'internship': internship,
        'student': internship.student,
    }
    return render(request, 'faculty_evaluator/lock_marks.html', context)


@login_required
@user_passes_test(is_faculty_evaluator)
def assessment_history(request):
    """View assessment history"""
    assessments = AssessmentMarks.objects.filter(
        evaluator=request.user
    ).select_related('internship_record__student', 'internship_record__organisation').order_by('-created_at')
    
    paginator = Paginator(assessments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_tab': 'evaluator_history',
        'assessments': page_obj,
    }
    return render(request, 'faculty_evaluator/assessment_history.html', context)