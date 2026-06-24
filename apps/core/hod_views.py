from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Student, InternshipRecord, ConsolidatedScore
from .decorators import hod_required
from apps.utils.calculations import calculate_student_consolidated_marks

@hod_required
def hod_dashboard(request):
    """HOD Dashboard"""
    context = {
        'total_students': Student.objects.count(),
        'completed_internships': InternshipRecord.objects.filter(completion_status='completed').count(),
        'pending_approvals': 0,  # Add logic
        'active_tab': 'hod_dashboard'
    }
    return render(request, 'hod/dashboard.html', context)

@hod_required
def student_list(request):
    """View all students (HOD view)"""
    students = Student.objects.select_related('department', 'programme', 'batch')
    if request.user.profile.department_id:
        students = students.filter(department=request.user.profile.department)
    return render(request, 'hod/students.html', {'students': students, 'active_tab': 'hod_students'})

@hod_required
def reports(request):
    """Reports page"""
    return render(request, 'admin/reports.html', {'active_tab': 'hod_reports'})

@hod_required
def consolidated_report(request):
    """Consolidated marks report"""
    students = Student.objects.select_related('programme')
    if request.user.profile.department_id:
        students = students.filter(department=request.user.profile.department)
    for student in students:
        data = calculate_student_consolidated_marks(student)
        ConsolidatedScore.objects.update_or_create(
            student=student,
            calculation_formula=data.get('formula_used', 'Default (Simple Average)'),
            defaults={
                'regular_internship_average': data.get('regular_average') or 0,
                'assessment_internship_score': data.get('assessment_score'),
                'final_consolidated_score': data.get('final_score') or 0,
            }
        )
    scores = ConsolidatedScore.objects.filter(student__in=students).select_related('student')
    return render(request, 'hod/consolidated_report.html', {'scores': scores, 'active_tab': 'hod_consolidated_report'})

@hod_required
def batch_report(request):
    """Batch-wise report"""
    return render(request, 'hod/batch_report.html')

@hod_required
def organisation_report(request):
    """Organisation-wise report"""
    return render(request, 'hod/organisation_report.html')

@hod_required
def mentor_report(request):
    """Mentor-wise report"""
    return render(request, 'hod/mentor_report.html')

@hod_required
def approvals(request):
    """Pending approvals"""
    internships = InternshipRecord.objects.filter(
        verification_status='verified',
        completion_status='pending'
    )
    return render(request, 'hod/approvals.html', {'internships': internships, 'active_tab': 'hod_approvals'})

@hod_required
def approve_record(request, pk):
    """Approve record"""
    record = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        record.verification_status = 'approved'
        record.save()
        messages.success(request, 'Record approved successfully!')
        return redirect('hod_approvals')
    return render(request, 'hod/approve.html', {'record': record})

@hod_required
def reject_record(request, pk):
    """Reject record"""
    record = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        record.verification_status = 'rejected'
        record.save()
        messages.success(request, 'Record rejected!')
        return redirect('hod_approvals')
    return render(request, 'hod/reject.html', {'record': record})
