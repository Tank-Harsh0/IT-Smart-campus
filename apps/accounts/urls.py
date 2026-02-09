from django.urls import path
from .views import CustomLoginView, PasswordChangeViewEnhanced, logout_view

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-change/', PasswordChangeViewEnhanced.as_view(), name='change_password'),
]