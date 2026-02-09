import numpy as np
import json
from django.db import models
from apps.students.models import Student
from apps.subjects.models import Subject

class FaceData(models.Model):
    """
    Stores the face encoding for a student.
    We store the encoding as a JSON list or binary blob.
    """
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='face_data')
    face_image = models.ImageField(upload_to='face_datasets/') # Reference image
    encoding_json = models.TextField() # Store numpy array as list
    
    created_at = models.DateTimeField(auto_now_add=True)

    def set_encoding(self, numpy_encoding):
        self.encoding_json = json.dumps(numpy_encoding.tolist())

    def get_encoding(self):
        return np.array(json.loads(self.encoding_json))

class AttendanceSession(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=True) # Session is active/closed
    
    def __str__(self):
        return f"{self.subject.name} - {self.date}"

class AttendanceRecord(models.Model):
    METHOD_CHOICES = [
        ('MANUAL', 'Manual'),
        ('FACE', 'Face Recognition'),
    ]
    
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_present = models.BooleanField(default=False)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='MANUAL')
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')