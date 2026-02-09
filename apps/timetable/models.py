from django.db import models
from apps.subjects.models import Subject

class Timetable(models.Model):
    DAYS_OF_WEEK = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
    ]

    semester = models.PositiveIntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=20)

    class Meta:
        ordering = ['day', 'start_time']
        # Prevent double booking a room at the same time (basic constraint)
        unique_together = ('day', 'start_time', 'room_number')

    def __str__(self):
        return f"Sem {self.semester} | {self.day} {self.start_time} | {self.subject.code}"