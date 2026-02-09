from django.contrib.auth import login, logout, update_session_auth_hash
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .forms import UserLoginForm, CustomPasswordChangeForm

class CustomLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        # Authenticate user
        user = form.get_user()
        login(self.request, user)
        
        # CHECK: Forced Password Change
        if user.must_change_password:
            messages.warning(self.request, "Security Policy: You must change your password to proceed.")
            return redirect('change_password')

        # CHECK: Role Based Redirect
        if user.is_admin:
            return redirect('admin_dashboard')
        elif user.is_faculty:
            return redirect('faculty_dashboard')
        elif user.is_student:
            return redirect('student_dashboard')
            
        return super().form_valid(form)

class PasswordChangeViewEnhanced(LoginRequiredMixin, PasswordChangeView):
    """
    Enhanced password change view that:
    1. Keeps users logged in after password change (update_session_auth_hash)
    2. Redirects to role-specific dashboard/profile
    3. Works for both forced and voluntary password changes
    """
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/change_password.html'
    
    def form_valid(self, form):
        user = form.save()
        # Keep user logged in after password change
        update_session_auth_hash(self.request, user)
        
        # Clear forced password change flag if set
        if hasattr(user, 'must_change_password') and user.must_change_password:
            user.must_change_password = False
            user.save()
        
        messages.success(self.request, "Your password has been changed successfully!")
        
        # Role-based redirect
        if user.is_admin:
            return redirect('admin_dashboard')
        elif user.is_faculty:
            return redirect('faculty_profile')
        elif user.is_student:
            return redirect('student_profile')
        
        return redirect('home')

def logout_view(request):
    logout(request)
    return redirect('index')