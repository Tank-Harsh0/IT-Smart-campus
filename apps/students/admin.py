from django.contrib import admin
from .models import Result, Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'enrollment_number', 'semester', 'attendance_percentage')
    search_fields = ('user__first_name', 'user__last_name', 'enrollment_number')
    list_filter = ('semester',)

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'
@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student','subject','exam_name','marks_obtained','total_marks','grade_display','percentage_display','pass_status',
    )
    list_filter = ('subject', 'exam_name')
    search_fields = ('student__user__username', 'subject__name', 'subject__code')

    def grade_display(self, obj):
        return obj.grade
    grade_display.short_description = "Grade"

    def percentage_display(self, obj):
        return round(obj.percentage(), 2)
    percentage_display.short_description = "Percentage"

    def pass_status(self, obj):
        return "PASS" if obj.is_passed() else "FAIL"
    pass_status.short_description = "Status"
