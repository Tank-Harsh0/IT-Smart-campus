from django.db import models
from apps.faculty.models import Faculty

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    semester = models.PositiveIntegerField()
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects')
    syllabus_url = models.URLField(max_length=300, blank=True, null=True, help_text="Link to GTU syllabus PDF")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name} (Sem {self.semester})"

    class Meta:
        unique_together = ('code', 'semester')
        ordering = ['semester', 'code']