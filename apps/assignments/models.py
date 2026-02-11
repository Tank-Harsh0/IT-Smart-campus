import os
from django.db import models
from apps.subjects.models import Subject

def assignment_upload_path(instance, filename):
    return os.path.join('assignments', instance.subject.code, filename)

class Assignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to=assignment_upload_path, blank=True, null=True) # Faculty upload
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
