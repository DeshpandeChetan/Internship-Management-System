from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import InternshipRecord, AssessmentMarks, AssessmentComponent
from .decorators import evaluator_required

@evaluator_required
def evaluator_dashboard(request):
    """Evaluator Dashboard"""
    context = {
        'pending_assessments': 0,  # Add logic
        'total_assessments': 0,    # Add logic
        'active_tab': 'evaluator_dashboard'
    }
    return render(request, 'evaluator/dashboard.html', context)

@evaluator_required
def pending_assessments(request):
    """View pending assessments"""
    internships = InternshipRecord.objects.filter(
        verification_status='verified'
    ).exclude(
        assessment_marks__isnull=False
    )
    return render(request, 'evaluator/pending_assessments.html', {
        'internships': internships,
        'active_tab': 'evaluator_pending_assessments'
    })

@evaluator_required
def enter_marks(request, pk):
    """Enter marks for assessment"""
    internship = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        messages.success(request, 'Marks entered successfully!')
        return redirect('evaluator_pending_assessments')
    return render(request, 'evaluator/enter_marks.html', {'internship': internship})

@evaluator_required
def edit_marks(request, pk):
    """Edit existing marks"""
    marks = get_object_or_404(AssessmentMarks, pk=pk)
    if request.method == 'POST':
        messages.success(request, 'Marks updated successfully!')
        return redirect('evaluator_history')
    return render(request, 'evaluator/edit_marks.html', {'marks': marks})

@evaluator_required
def assessment_history(request):
    """View assessment history"""
    marks = AssessmentMarks.objects.filter(
        evaluator=request.user
    ).select_related('internship_record', 'assessment_component')
    return render(request, 'evaluator/history.html', {
        'marks': marks,
        'active_tab': 'evaluator_history'
    })