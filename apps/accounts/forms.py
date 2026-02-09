from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

class UserLoginForm(AuthenticationForm):
    # You can add custom styling widgets here for Tailwind
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Username or Email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Password'
    }))

class CustomPasswordChangeForm(PasswordChangeForm):
    # Just styling
    pass