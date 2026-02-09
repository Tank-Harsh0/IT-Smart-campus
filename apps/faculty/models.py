from django.db import models
from apps.accounts.models import User

class Faculty(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    
    # --- New Fields from Profile Card ---
    designation = models.CharField(max_length=100, default="Lecturer") # e.g. Lecturer (Senior Scale)
    qualification = models.CharField(max_length=100, blank=True)       # e.g. M.E., Ph.D.
    
    dept_joining_date = models.DateField(null=True, blank=True)        # e.g. 16th March 2005
    institute_joining_date = models.DateField(null=True, blank=True)   # e.g. 6th December 2013
    
    area_of_interest = models.TextField(blank=True)                    # e.g. Software Engg., JAVA
    courses_taught = models.TextField(blank=True)                      # e.g. JAVA, Python
    
    portfolio = models.CharField(max_length=200, blank=True) 
    photo = models.ImageField(upload_to='faculty_photos/', blank=True, null=True)          # e.g. COGENT Coordinator
    initials = models.CharField(max_length=5, blank=True, help_text="e.g. KKP, BGP")
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.designation})"