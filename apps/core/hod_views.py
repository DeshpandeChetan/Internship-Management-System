from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Student, InternshipRecord, ConsolidatedScore, AssessmentMarks
from .decorators import hod_required
from apps.utils.calculations import calculate_student_consolidated_marks, calculate_student_internship_progress
from apps.utils.audit import log_action

@hod_required
def hod_dashboard(request):
    """HOD Dashboard"""
    students = Student.objects.select_related('department', 'programme', 'batch')
    internships = InternshipRecord.objects.select_related('student', 'organisation')
    if request.user.profile.department_id:
        students = students.filter(department=request.user.profile.department)
        internships = internships.filter(student__department=request.user.profile.department)

    verification_counts = {
        row['verification_status']: row['count']
        for row in internships.values('verification_status').annotate(count=Count('id'))
    }
    completion_counts = {
        row['completion_status']: row['count']
        for row in internships.values('completion_status').annotate(count=Count('id'))
    }
    programme_rows = students.values('programme__code').annotate(count=Count('id')).order_by('programme__code')
    marks = AssessmentMarks.objects.filter(internship_record__in=internships)
    marks_status_counts = {
        row['status']: row['count']
        for row in marks.values('status').annotate(count=Count('id'))
    }

    context = {
        'total_students': students.count(),
        'total_internships': internships.count(),
        'completed_internships': internships.filter(completion_status='completed').count(),
        'pending_approvals': internships.filter(verification_status='verified', completion_status='pending').count(),
        'pending_verifications': internships.filter(verification_status='submitted').count(),
        'verification_chart': {
            'labels': [label for value, label in InternshipRecord.VERIFICATION_STATUS],
            'data': [verification_counts.get(value, 0) for value, label in InternshipRecord.VERIFICATION_STATUS],
        },
        'completion_chart': {
            'labels': [label for value, label in InternshipRecord.COMPLETION_STATUS],
            'data': [completion_counts.get(value, 0) for value, label in InternshipRecord.COMPLETION_STATUS],
        },
        'programme_chart': {
            'labels': [row['programme__code'] or 'Unassigned' for row in programme_rows],
            'data': [row['count'] for row in programme_rows],
        },
        'marks_status_chart': {
            'labels': [label for value, label in AssessmentMarks.STATUS_CHOICES],
            'data': [marks_status_counts.get(value, 0) for value, label in AssessmentMarks.STATUS_CHOICES],
        },
        'recent_internships': internships.order_by('-created_on')[:8],
        'active_tab': 'hod_dashboard'
    }
    return render(request, 'hod/dashboard.html', context)

@hod_required
def student_list(request):
    """View all students (HOD view)"""
    students = Student.objects.select_related('department', 'programme', 'batch')
    if request.user.profile.department_id:
        students = students.filter(department=request.user.profile.department)
    rows = [
        {
            'student': student,
            'progress': calculate_student_internship_progress(student),
        }
        for student in students
    ]
    return render(request, 'hod/students.html', {'rows': rows, 'active_tab': 'hod_students'})

@hod_required
def reports(request):
    """Reports page"""
    from . import admin_views
    context = {'active_tab': 'hod_reports'}
    context.update(admin_views._report_filter_context())
    return render(request, 'admin/reports.html', context)

@hod_required
def consolidated_report(request):
    """Consolidated marks report"""
    top_n = request.GET.get('top_n')
    try:
        top_n = int(top_n) if top_n else None
    except (TypeError, ValueError):
        top_n = None

    students = Student.objects.select_related('programme')
    if request.user.profile.department_id:
        students = students.filter(department=request.user.profile.department)
    rows = []
    for student in students:
        data = calculate_student_consolidated_marks(student, top_n=top_n)
        ConsolidatedScore.objects.update_or_create(
            student=student,
            calculation_formula=data.get('formula_used', 'Default (Simple Average)'),
            defaults={
                'regular_internship_average': data.get('regular_average') or 0,
                'assessment_internship_score': data.get('assessment_score'),
                'final_consolidated_score': data.get('final_score') or 0,
            }
        )
        rows.append({'student': student, 'data': data})
    return render(request, 'hod/consolidated_report.html', {
        'rows': rows,
        'selected_top_n': top_n or 5,
        'active_tab': 'hod_consolidated_report'
    })

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
    """Approve record.

    NOTE: 'approved' is not a valid InternshipRecord.verification_status choice
    (draft/submitted/verified/needs_correction/rejected). The `approvals()`
    queue above lists records that are already verification_status='verified'
    but still completion_status='pending' - so HoD approval here finalizes
    completion, not verification, which was already done by the mentor.
    """
    record = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        old_completion_status = record.completion_status
        record.completion_status = 'completed'
        record.save(update_fields=['completion_status', 'updated_on'])
        log_action(
            request, 'APPROVE', 'InternshipRecord', record_id=record.id,
            old_value=old_completion_status, new_value=record.completion_status
        )
        messages.success(request, 'Record approved successfully!')
        return redirect('hod_approvals')
    return render(request, 'hod/approve.html', {'record': record})

@hod_required
def reject_record(request, pk):
    """Reject record"""
    record = get_object_or_404(InternshipRecord, pk=pk)
    if request.method == 'POST':
        old_status = record.verification_status
        record.verification_status = 'rejected'
        record.save()
        log_action(
            request, 'REJECT', 'InternshipRecord', record_id=record.id,
            old_value=old_status, new_value=record.verification_status
        )
        messages.success(request, 'Record rejected!')
        return redirect('hod_approvals')
    return render(request, 'hod/reject.html', {'record': record})
