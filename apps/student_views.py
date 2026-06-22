# Internship-Management-System\apps\student_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.forms import HiddenInput

from .models import (
    Student, InternshipRecord, Organisation, BreakRecord,
    MentorAssignment, AssessmentMarks, Document, Notification
)
from .forms import (
    InternshipRecordForm, BreakRecordForm, DocumentUploadForm
)
from .utils.permissions import is_student
from .utils.calculations import calculate_student_consolidated_marks


@login_required
@user_passes_test(is_student)
def dashboard(request):
    """Student dashboard showing overview"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found. Please contact administrator.')
        return redirect('home')
    
    # Get current mentor
    current_mentor = student.current_mentor
    
    # Statistics
    total_internships = student.internship_records.count()
    completed_internships = student.internship_records.filter(completion_status='completed').count()
    pending_verifications = student.internship_records.filter(verification_status='submitted').count()
    needs_correction = student.internship_records.filter(verification_status='needs_correction').count()
    
    # Recent internships
    recent_internships = student.internship_records.all().order_by('-created_at')[:5]
    
    # Active breaks
    active_breaks = student.breaks.filter(
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    )
    
    # Notifications
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
    
    context = {
        'active_tab': 'student_dashboard',
        'student': student,
        'current_mentor': current_mentor,
        'total_internships': total_internships,
        'completed_internships': completed_internships,
        'pending_verifications': pending_verifications,
        'needs_correction': needs_correction,
        'recent_internships': recent_internships,
        'active_breaks': active_breaks,
        'notifications': notifications,
    }
    return render(request, 'student/dashboard.html', context)


@login_required
@user_passes_test(is_student)
def my_internships(request):
    """List all internships of the student"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    internships = student.internship_records.all().order_by('internship_number')
    
    context = {
        'active_tab': 'my_internships',
        'internships': internships,
        'student': student,
    }
    return render(request, 'student/internships.html', context)


@login_required
@user_passes_test(is_student)
def add_internship(request):
    """Add a new internship record"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    # Check internship limits
    regular_count = student.internship_records.filter(internship_type='regular').count()
    max_regular = 8
    
    if request.method == 'POST':
        form = InternshipRecordForm(request.POST, request.FILES)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.student = student
            internship.verification_status = 'draft'
            
            # Auto-assign internship number for regular internships
            if internship.internship_type == 'regular' and not internship.internship_number:
                internship.internship_number = regular_count + 1
            
            internship.save()
            
            # Handle file uploads
            if 'certificate_upload' in request.FILES:
                internship.certificate_upload = request.FILES['certificate_upload']
            if 'report_upload' in request.FILES:
                internship.report_upload = request.FILES['report_upload']
            internship.save()
            
            messages.success(request, 'Internship record added successfully!')
            return redirect('student_internships')
    else:
        form = InternshipRecordForm()
        # Limit organisation choices to active ones
        form.fields['organisation'].queryset = Organisation.objects.filter(status='active')
    
    context = {
        'active_tab': 'add_internship',
        'form': form,
        'student': student,
        'regular_count': regular_count,
        'max_regular': max_regular,
    }
    return render(request, 'student/add_internship.html', context)


@login_required
@user_passes_test(is_student)
def edit_internship(request, internship_id):
    """Edit an existing internship record"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    internship = get_object_or_404(InternshipRecord, id=internship_id, student=student)
    
    # Check if internship is editable
    if internship.verification_status in ['verified', 'locked']:
        messages.error(request, 'This internship cannot be edited as it is already verified/locked.')
        return redirect('student_internships')
    
    if request.method == 'POST':
        form = InternshipRecordForm(request.POST, request.FILES, instance=internship)
        if form.is_valid():
            internship = form.save(commit=False)
            internship.verification_status = 'draft'  # Reset to draft on edit
            internship.save()
            
            messages.success(request, 'Internship record updated successfully!')
            return redirect('student_internships')
    else:
        form = InternshipRecordForm(instance=internship)
        form.fields['organisation'].queryset = Organisation.objects.filter(status='active')
    
    context = {
        'active_tab': 'my_internships',
        'form': form,
        'internship': internship,
        'student': student,
    }
    return render(request, 'student/edit_internship.html', context)


@login_required
@user_passes_test(is_student)
def submit_internship(request, internship_id):
    """Submit internship for verification"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    internship = get_object_or_404(InternshipRecord, id=internship_id, student=student)
    
    if internship.verification_status in ['submitted', 'verified', 'locked']:
        messages.warning(request, 'Internship already submitted/verified.')
        return redirect('student_internships')
    
    internship.verification_status = 'submitted'
    internship.student_submission_date = timezone.now()
    internship.save()
    
    # Notify faculty mentor
    current_mentor = student.current_mentor
    if current_mentor and current_mentor.faculty_mentor:
        from .utils.notifications import send_notification
        send_notification(
            recipient=current_mentor.faculty_mentor,
            title='Internship Submitted for Verification',
            message=f'Student {student.name} has submitted internship at {internship.organisation.name} for verification.',
            notification_type='info',
            link=f'/teacher/verify-internship/{internship.id}/'
        )
    
    messages.success(request, 'Internship submitted for verification successfully!')
    return redirect('student_internships')


@login_required
@user_passes_test(is_student)
def internship_details(request, internship_id):
    """View details of a specific internship"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    internship = get_object_or_404(InternshipRecord, id=internship_id, student=student)
    assessment_marks = internship.assessment_marks.all()
    
    context = {
        'active_tab': 'my_internships',
        'internship': internship,
        'assessment_marks': assessment_marks,
        'student': student,
    }
    return render(request, 'student/internship_detail.html', context)


@login_required
@user_passes_test(is_student)
def add_break(request):
    """Add a break record (academic/internship break)"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    if request.method == 'POST':
        form = BreakRecordForm(request.POST, request.FILES, initial={'student': student})
        form.fields['student'].widget = HiddenInput()
        if form.is_valid():
            break_record = form.save(commit=False)
            break_record.student = student
            
            if 'supporting_document' in request.FILES:
                break_record.supporting_document = request.FILES['supporting_document']
            
            break_record.save()
            
            # Update student status if on break
            if break_record.break_type in ['academic', 'medical']:
                student.current_status = 'on_break'
                student.save()
            
            messages.success(request, 'Break record added successfully!')
            return redirect('student_breaks')
    else:
        form = BreakRecordForm(initial={'student': student})
        form.fields['student'].widget = HiddenInput()
    
    context = {
        'active_tab': 'add_break',
        'form': form,
        'student': student,
    }
    return render(request, 'student/add_break.html', context)


@login_required
@user_passes_test(is_student)
def my_breaks(request):
    """List all break records"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    breaks = student.breaks.all().order_by('-start_date')
    
    context = {
        'active_tab': 'my_breaks',
        'breaks': breaks,
        'student': student,
    }
    return render(request, 'student/breaks.html', context)


@login_required
@user_passes_test(is_student)
def my_marks(request):
    """View all marks for internships"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    internships = student.internship_records.filter(completion_status='completed')
    
    marks_data = []
    for internship in internships:
        viva_marks = internship.viva_marks
        intermediate_marks = internship.intermediate_marks_list
        marks_data.append({
            'internship': internship,
            'viva_marks': viva_marks,
            'intermediate_marks': intermediate_marks,
        })
    
    # Calculate consolidated marks
    consolidated_data = calculate_student_consolidated_marks(student)
    
    context = {
        'active_tab': 'my_marks',
        'marks_data': marks_data,
        'consolidated_data': consolidated_data,
        'student': student,
    }
    return render(request, 'student/marks.html', context)


@login_required
@user_passes_test(is_student)
def upload_document(request, internship_id=None):
    """Upload supporting documents"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.student = student
            document.uploaded_by = request.user
            
            if internship_id:
                document.internship_record_id = internship_id
            
            if 'file' in request.FILES:
                document.file = request.FILES['file']
            
            document.save()
            messages.success(request, 'Document uploaded successfully!')
            
            if internship_id:
                return redirect('student_internship_details', internship_id=internship_id)
            return redirect('student_documents')
    else:
        form = DocumentUploadForm()
    
    context = {
        'active_tab': 'upload_document',
        'form': form,
        'internship_id': internship_id,
    }
    return render(request, 'student/upload_document.html', context)


@login_required
@user_passes_test(is_student)
def my_documents(request):
    """List all uploaded documents"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    documents = student.documents.all().order_by('-uploaded_at')
    
    context = {
        'active_tab': 'my_documents',
        'documents': documents,
    }
    return render(request, 'student/documents.html', context)


@login_required
@user_passes_test(is_student)
def view_mentor(request):
    """View current mentor details"""
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    current_mentor = student.current_mentor
    mentor_history = student.mentor_assignments.all().order_by('-effective_from')
    
    context = {
        'active_tab': 'view_mentor',
        'current_mentor': current_mentor,
        'mentor_history': mentor_history,
    }
    return render(request, 'student/mentor.html', context)