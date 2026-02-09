from django.urls import path
from .views import exam_list, create_exam

urlpatterns = [
    path('', exam_list, name='exam_list'),
    path('create/', create_exam, name='create_exam'),
]