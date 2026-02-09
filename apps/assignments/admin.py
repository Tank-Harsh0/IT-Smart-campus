from django.contrib import admin
from .models import Assignment

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'due_date', 'created_at')
    list_filter = ('subject__semester', 'due_date')
    search_fields = ('title', 'subject__name')
