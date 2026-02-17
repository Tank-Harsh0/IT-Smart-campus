from django.urls import path
from . import views

urlpatterns = [
    path('', views.discussion_list, name='discussion_list'),
    path('create/', views.discussion_create, name='discussion_create'),
    path('<int:discussion_id>/', views.discussion_detail, name='discussion_detail'),
    path('<int:discussion_id>/pin/', views.discussion_pin, name='discussion_pin'),
    path('<int:discussion_id>/close/', views.discussion_close, name='discussion_close'),
]
