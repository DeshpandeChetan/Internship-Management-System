from django.shortcuts import redirect
from django.contrib import messages

class UserApprovalMiddleware:
    """Middleware to check if user is approved before accessing pages"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                if not profile.can_login():
                    # Logout the user and show message
                    from django.contrib.auth import logout
                    logout(request)
                    messages.error(request, 'Your account is pending admin approval or has been deactivated. Please contact administrator.')
                    return redirect('login')
        response = self.get_response(request)
        return response