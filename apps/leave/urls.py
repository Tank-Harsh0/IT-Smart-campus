from django.urls import path
from . import views

urlpatterns = [
    # Faculty
    path('faculty/apply/', views.faculty_leave_apply, name='faculty_leave_apply'),
    path('faculty/history/', views.faculty_leave_history, name='faculty_leave_history'),

    # Admin
    path('admin/requests/', views.admin_leave_requests, name='admin_leave_requests'),
    path('admin/<int:leave_id>/action/', views.admin_leave_action, name='admin_leave_action'),

    # Student
    path('student/absent-faculty/', views.student_faculty_absent, name='student_faculty_absent'),
]
