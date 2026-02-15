from django.contrib import admin
from .models import Exam, ExamSubject, ExamResult


class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'exam_type', 'semester', 'start_date', 'end_date', 'is_published')
    list_filter = ('exam_type', 'semester', 'is_published')
    inlines = [ExamSubjectInline]


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'exam', 'marks_obtained', 'total_marks', 'graded_by')
    list_filter = ('exam', 'subject')
    search_fields = ('student__user__first_name', 'student__enrollment_number')
