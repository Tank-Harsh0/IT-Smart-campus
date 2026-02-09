from django.urls import path
from .views import start_session, recognize_face

urlpatterns = [
    path('session/start/<int:subject_id>/', start_session, name='start_session'),
    path('recognize/<int:session_id>/', recognize_face, name='recognize_face'),
]