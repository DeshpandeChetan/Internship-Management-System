# apps/core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .decorators import role_required
from django.contrib import messages

@login_required
def dashboard_redirect(request):
    """Redirect to role-specific dashboard"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'User profile not found. Please contact admin.')
        return redirect('login')
    
    role = request.user.profile.role
    
    dashboard_urls = {
        'admin': 'admin_dashboard',
        'dept_admin': 'admin_dashboard',
        'faculty_mentor': 'mentor_dashboard',
        'evaluator': 'evaluator_dashboard',
        'hod': 'hod_dashboard',
        'student': 'student_dashboard',
    }
    
    return redirect(dashboard_urls.get(role, 'student_dashboard'))

@login_required
def profile_view(request):
    """View user profile"""
    return render(request, 'admin/profile.html', {'active_tab': 'profile'})

@login_required
def profile_update(request):
    """Update user profile via modal"""
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()
        
        if phone_number:
            profile = user.profile
            profile.phone_number = phone_number
            profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return redirect('profile')

@login_required
def report_list(request):
    """List all available reports"""
    return render(request, 'admin/reports.html', {'active_tab': 'admin_reports'})

@login_required
def export_report(request, report_type):
    """Export report in Excel/PDF format"""
    return HttpResponse(f"Exporting {report_type} report...")

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler403(request, exception):
    return render(request, '403.html', status=403)

def handler500(request):
    return render(request, '500.html', status=500)