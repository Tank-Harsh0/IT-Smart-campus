from django.urls import path
from .views import (admin_dashboard, Upload_subjects,Upload_students, download_sample_csv, 
                    subject_list, download_sample_subjects_csv, 
                    student_list, Faculty_list, upload_batches, 
                    upload_timetable, auto_generate_batches, load_subjects,load_classrooms,load_batches, index,
                    faculty_public, curriculum, gallery)

urlpatterns = [
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('', index, name='index'),
    
    # Public Pages (No Login Required) - Accessible without authentication
    path('about-faculty/', faculty_public, name='faculty_public'),
    path('about-curriculum/', curriculum, name='curriculum'),
    path('about-gallery/', gallery, name='gallery'),
    
    path('students/', student_list, name='student_list'),
    path('faculty/', Faculty_list, name='Faculty_list'),
    path('subjects/', subject_list, name='subject_list'),
    path('upload/students/', Upload_students, name='Upload_students'),
    path('upload/subject/', Upload_subjects, name='Upload_subjects'),
    path('upload/sample-csv/', download_sample_csv, name='download_sample_csv'),
    path('upload/sample-subjects-csv/', download_sample_subjects_csv, name='download_sample_subjects_csv'),
    path('upload/batches/', upload_batches, name='upload_batches'),
    path('upload/timetable/', upload_timetable, name='upload_timetable'),
    path('batches/auto-generate/', auto_generate_batches, name='auto_generate_batches'),
    path('ajax/load-subjects/', load_subjects, name='ajax_load_subjects'),
    path('ajax/load-classrooms/', load_classrooms, name='ajax_load_classrooms'),
    path('ajax/load-batches/', load_batches, name='ajax_load_batches'),
]