from django.contrib import admin
from .models import Faculty

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'employee_id', 'designation')
    search_fields = ('user__first_name', 'user__last_name', 'employee_id')
    list_filter = ('designation',)

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'