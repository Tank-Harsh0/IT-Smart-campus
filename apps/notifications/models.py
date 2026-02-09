from django.db import models

class Notification(models.Model):
    AUDIENCE_CHOICES = [
        ('ALL', 'All Users'),
        ('STUDENT', 'Students Only'),
        ('FACULTY', 'Faculty Only'),
    ]
    
    PRIORITY_CHOICES = [
        ('NORMAL', 'Normal'),
        ('HIGH', 'Urgent / High'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default='ALL')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.audience})"