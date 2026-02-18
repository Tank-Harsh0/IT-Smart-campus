from django.urls import path
from . import views

urlpatterns = [
    path('admin/ml-insights/', views.admin_ml_dashboard, name='admin_ml_dashboard'),
    path('faculty/anomaly-alerts/', views.faculty_anomaly_alerts, name='faculty_anomaly_alerts'),
]
