from django.db import models
from django.utils import timezone
from apps.students.models import Student
from apps.subjects.models import Subject
from apps.faculty.models import Faculty


class Exam(models.Model):
    EXAM_TYPES = [
        ('MID', 'Mid-Semester'),
        ('END', 'End-Semester'),
        ('REM', 'Remedial'),
        ('PRAC', 'Practical'),
    ]

    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPES, default='MID')
    semester = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    # Publish control
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Sem {self.semester})"

    @property
    def is_over(self):
        """Check if exam end date has passed."""
        return self.end_date < timezone.now().date()

    @property
    def grading_progress(self):
        """Returns dict with total expected results and graded count."""
        total = ExamResult.objects.filter(exam=self).count()
        graded = ExamResult.objects.filter(exam=self, marks_obtained__isnull=False).count()
        return {'total': total, 'graded': graded}


class ExamSubject(models.Model):
    """Links subjects to an exam with per-subject total marks."""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    total_marks = models.PositiveIntegerField(default=20)

    class Meta:
        unique_together = ('exam', 'subject')

    def __str__(self):
        return f"{self.exam.name} - {self.subject.code} ({self.total_marks} marks)"


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results')
    marks_obtained = models.IntegerField(null=True, blank=True)
    total_marks = models.PositiveIntegerField(default=20)
    graded_by = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('exam', 'subject', 'student')

    def __str__(self):
        return f"{self.student} - {self.subject.code} - {self.exam.name}"

    @property
    def percentage(self):
        if not self.marks_obtained or self.total_marks == 0:
            return 0
        return round((self.marks_obtained / self.total_marks) * 100, 2)

    @property
    def grade(self):
        p = self.percentage
        if p >= 90: return "A+"
        if p >= 80: return "A"
        if p >= 70: return "B"
        if p >= 60: return "C"
        if p >= 50: return "D"
        return "F"

    @property
    def is_passed(self):
        return self.percentage >= 50


class ExamSchedule(models.Model):
    """Per-subject schedule: date, time slot, and room for an exam."""
    exam_subject = models.OneToOneField(ExamSubject, on_delete=models.CASCADE, related_name='schedule')
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f"{self.exam_subject} on {self.exam_date} ({self.start_time}-{self.end_time})"