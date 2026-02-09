from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    
    # Attendance Stats (Renamed to match template)
    path('attendance/', views.attendance_stats, name='student_attendance_stats'), 
    
    # Assignments
    path('assignments/', views.assignment_list, name='student_assignment_list'),
    
    # Results
    path('results/', views.student_results, name='student_results'),
    
    # Timetable
    path('timetable/', views.student_timetable, name='student_timetable'),
    
    # Face Registration
    path('register-face/', views.register_face_view, name='register_face_view'),
    
    # Profile
    path('profile/', views.student_profile, name='student_profile'),
    path('notifications/', views.student_notifications, name='student_notifications'),
]