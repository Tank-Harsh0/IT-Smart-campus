from django.contrib import admin
from .models import Subject

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'semester', 'faculty')
    search_fields = ('name', 'code')
    list_filter = ('semester', 'faculty')
    ordering = ('semester', 'code')