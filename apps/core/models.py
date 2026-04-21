from django.db import models
from apps.faculty.models import Faculty
from apps.subjects.models import Subject


class Classroom(models.Model):
    name = models.CharField(max_length=20, unique=True) 
    semester = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name

class Batch(models.Model):
    name = models.CharField(max_length=20, unique=True) 
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='batches')
    
    def __str__(self):
        return self.name


class TimetableSlot(models.Model):
    DAYS = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday')
    ]

    day = models.CharField(max_length=3, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    
    room_number = models.CharField(max_length=10)
    
    class Meta:
        unique_together = ('day', 'start_time', 'faculty') 

    def __str__(self):
        return f"{self.day} | {self.subject.code} | {self.batch.name}"