from django.db import models
from apps.accounts.models import User

class Faculty(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    
    
    designation = models.CharField(max_length=100, default="Lecturer")
    qualification = models.CharField(max_length=100, blank=True)
    
    dept_joining_date = models.DateField(null=True, blank=True)
    institute_joining_date = models.DateField(null=True, blank=True)
    
    area_of_interest = models.TextField(blank=True)
    courses_taught = models.TextField(blank=True)
    
    portfolio = models.CharField(max_length=200, blank=True) 
    photo = models.ImageField(upload_to='faculty_photos/', blank=True, null=True)
    initials = models.CharField(max_length=5, blank=True, help_text="e.g. KKP, BGP")
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.designation})"