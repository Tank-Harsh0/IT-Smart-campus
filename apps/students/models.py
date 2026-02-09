from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

# Assuming these apps exist based on your imports
from apps.subjects.models import Subject
from apps.core.models import Batch

class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    enrollment_number = models.CharField(max_length=20, unique=True)
    semester = models.PositiveIntegerField(default=1)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    attendance_percentage = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.enrollment_number}"
    

class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    exam_name = models.CharField(max_length=50, default="Mid-Semester")
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)

    # --- REQUIRED BY VIEW ---
    credits = models.PositiveIntegerField(default=1)

    def percentage(self):
        if self.total_marks == 0:
            return 0
        return (self.marks_obtained / self.total_marks) * 100

    def calculate_points(self):
        p = self.percentage()
        if p >= 90:
            return 10
        if p >= 80:
            return 9
        if p >= 70:
            return 8
        if p >= 60:
            return 7
        if p >= 50:
            return 6
        return 0

    @property
    def grade(self):
        p = self.percentage()
        if p >= 90:
            return "A+"
        if p >= 80:
            return "A"
        if p >= 70:
            return "B"
        if p >= 60:
            return "C"
        if p >= 50:
            return "D"
        return "F"

    def is_passed(self):
        return self.percentage() >= 50
