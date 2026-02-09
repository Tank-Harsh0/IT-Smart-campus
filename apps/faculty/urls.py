from django.urls import path
from .views import faculty_dashboard, create_assignment, student_list, faculty_schedule, faculty_notifications, mark_notification_read, faculty_profile, edit_faculty_profile, download_schedule_pdf

urlpatterns = [
    path('dashboard/', faculty_dashboard, name='faculty_dashboard'),
    path('schedule/', faculty_schedule, name='faculty_schedule'),
    path('students/', student_list, name='faculty_student_list'),
    path('assignment/create/', create_assignment, name='create_assignment'),
    path('assignment/create/<int:subject_id>/', create_assignment, name='create_assignment_for_subject'),
    path('profile/', faculty_profile, name='faculty_profile'),
    path('profile/edit/', edit_faculty_profile, name='edit_faculty_profile'),
    path('notifications/', faculty_notifications, name='faculty_notifications'),
    path('notifications/read/<int:notification_id>/', mark_notification_read, name='mark_notification_read'),
    path('schedule/pdf/', download_schedule_pdf, name='download_schedule_pdf'),
]
