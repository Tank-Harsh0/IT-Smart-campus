from django.urls import path
from .views import (exam_list, create_exam, exam_detail,
                    publish_exam, unpublish_exam,
                    edit_exam, exam_timetable)

urlpatterns = [
    path('', exam_list, name='exam_list'),
    path('create/', create_exam, name='create_exam'),
    path('<int:exam_id>/', exam_detail, name='exam_detail'),
    path('<int:exam_id>/edit/', edit_exam, name='edit_exam'),
    path('<int:exam_id>/timetable/', exam_timetable, name='exam_timetable'),
    path('<int:exam_id>/publish/', publish_exam, name='publish_exam'),
    path('<int:exam_id>/unpublish/', unpublish_exam, name='unpublish_exam'),
]