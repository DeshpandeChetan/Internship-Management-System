from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm

from .forms import StudentRegistrationForm

def home(request):
    return render(request, 'home/index.html', {'hide_sidebar': True, 'hide_header': True})

def about(request):
    return render(request, 'home/about.html', {'hide_sidebar': True, 'hide_header': True})

def contact(request):
    return render(request, 'home/contact.html', {'hide_sidebar': True, 'hide_header': True})

def login_view(request):
    """Google login only - no username/password"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/login.html', {'hide_sidebar': True, 'hide_header': True})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('login')
    return redirect('home')

def register_view(request):
    return redirect('login')

def register_student(request):
    return redirect('login')

def register_company(request):
    return redirect('login')


def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            messages.success(request, 'If the email exists, password reset instructions will be sent.')
            return redirect('login')
    else:
        form = PasswordResetForm()

    return render(request, 'accounts/password_reset.html', {
        'hide_sidebar': True,
        'hide_header': True,
        'form': form,
    })

def privacy_policy(request):
    return render(request, 'accounts/policy.html', {'hide_sidebar': True, 'hide_header': True})

def terms_of_service(request):
    return render(request, 'accounts/terms.html', {'hide_sidebar': True, 'hide_header': True})

@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on role"""
    if request.user.role == 'pending':
        messages.warning(request, 'Your account is pending admin approval.')
        return render(request, 'accounts/pending_approval.html', {'hide_sidebar': True})
    
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    if request.user.role in ['dept_admin', 'hod']:
        return redirect('admin_dashboard')  # Department admin uses similar dashboard
    if request.user.role == 'faculty_mentor':
        return redirect('faculty_mentor_dashboard')
    if request.user.role == 'faculty_evaluator':
        return redirect('evaluator_dashboard')
    if request.user.role == 'student':
        return redirect('student_dashboard')
    
    return redirect('home')

def custom_404(request, exception=None):
    return render(request, 'home/404.html', {'hide_sidebar': True, 'hide_header': True}, status=404)

def custom_500(request):
    return render(request, 'home/500.html', {'hide_sidebar': True, 'hide_header': True}, status=500)

def reports(request):
    return render(request, 'report/generate_report.html', {})

def load_internships(request):
    return HttpResponse("AJAX endpoint for loading internships")

def load_applications(request):
    return HttpResponse("AJAX endpoint for loading applications")