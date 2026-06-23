from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Student, InternshipRecord, MentorAssignment, AssessmentMarks
from .decorators import student_required
from .forms import InternshipForm

@student_required
def student_dashboard(request):
    """Student Dashboard"""
    # FIX: Use 'user' instead of 'user_profile'
    student = get_object_or_404(Student, user=request.user)
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
    student = get_object_or_404(Student, user=request.user)
    internships = InternshipRecord.objects.filter(student=student).order_by('-start_date')
    return render(request, 'student/internships.html', {'internships': internships, 'active_tab': 'my_internships'})

@student_required
def internship_add(request):
    """Add new internship"""
    student = get_object_or_404(Student, user=request.user)
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
    return render(request, 'student/internship_form.html', {'form': form, 'active_tab': 'my_internships'})

@student_required
def internship_detail(request, pk):
    """View internship details"""
    student = get_object_or_404(Student, user=request.user)
    internship = get_object_or_404(InternshipRecord, pk=pk, student=student)
    return render(request, 'student/internship_detail.html', {'internship': internship, 'active_tab': 'my_internships'})


@student_required
def internship_edit(request, pk):
    """Edit internship"""
    student = get_object_or_404(Student, user=request.user)
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
    return render(request, 'student/internship_form.html', {'form': form, 'active_tab': 'my_internships'})

@student_required
def internship_delete(request, pk):
    """Delete internship"""
    student = get_object_or_404(Student, user=request.user)
    internship = get_object_or_404(InternshipRecord, pk=pk, student=student)
    if request.method == 'POST':
        internship.delete()
        messages.success(request, 'Internship deleted successfully!')
        return redirect('my_internships')
    return render(request, 'student/internship_confirm_delete.html', {'internship': internship})

@student_required
def my_mentor(request):
    """View assigned mentor"""
    student = get_object_or_404(Student, user=request.user)
    assignment = MentorAssignment.objects.filter(
        student=student, 
        is_active=True
    ).first()
    return render(request, 'student/mentor.html', {'assignment': assignment, 'active_tab': 'my_mentor'})

@student_required
def my_marks(request):
    """View marks"""
    student = get_object_or_404(Student, user=request.user)
    marks = AssessmentMarks.objects.filter(
        internship_record__student=student
    ).select_related('internship_record', 'assessment_component')
    return render(request, 'student/marks.html', {'marks': marks, 'active_tab': 'my_marks'})

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