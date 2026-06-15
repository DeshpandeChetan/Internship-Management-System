# profile_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from .models import User, Student
from .forms import UserRegistrationForm


@login_required
def view_profile(request):
    """View user profile"""
    context = {
        'user': request.user,
        'active_tab': 'profile',
    }
    
    # Add student-specific info if user is student
    if hasattr(request.user, 'student_profile'):
        student = request.user.student_profile
        context['student'] = student
        context['internships'] = student.internship_records.order_by('internship_number')
        context['breaks'] = student.breaks.order_by('-start_date')
        context['current_status'] = student.current_status
    
    return render(request, 'profile/view.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('view_profile')
    
    return render(request, 'profile/edit.html', {'user': request.user})


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('view_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'profile/change_password.html', {'form': form})


@login_required
def notifications(request):
    """View user notifications"""
    notifications = request.user.notifications.all()
    
    # Mark as read
    if request.GET.get('mark_read'):
        notifications.filter(id=request.GET.get('mark_read')).update(is_read=True)
    elif request.GET.get('mark_all_read'):
        notifications.update(is_read=True)
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
    }
    return render(request, 'profile/notifications.html', context)