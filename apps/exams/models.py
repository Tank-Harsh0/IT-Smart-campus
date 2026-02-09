from django.db import models
from apps.students.models import Student
from apps.subjects.models import Subject

class Exam(models.Model):
    EXAM_TYPES = [
        ('MID', 'Mid-Semester'),
        ('REM', 'Remedial'),
        ('PRAC', 'Practical'),
    ]

    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPES, default='MID')
    
    # Link to Subject (Optional: If an exam covers a specific subject)
    # If exams are general (e.g. "Mid Sem" covers all subjects), remove this line.
    # subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    
    semester = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (Sem {self.semester})"
    
class ExamResult(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="results"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )
    marks_obtained = models.IntegerField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('exam', 'subject', 'student')

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.exam}"