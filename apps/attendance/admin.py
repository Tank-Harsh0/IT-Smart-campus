from django.contrib import admin
from .models import FaceData, AttendanceSession, AttendanceRecord

@admin.register(FaceData)
class FaceDataAdmin(admin.ModelAdmin):
    list_display = ('student', 'has_encoding')
    search_fields = ('student__user__first_name', 'student__enrollment_number')
    
    def has_encoding(self, obj):
        return bool(obj.encoding_json)
    has_encoding.boolean = True

class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    can_delete = False
    readonly_fields = ('student', 'timestamp', 'method', 'is_present')

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'date', 'status')
    list_filter = ('date', 'subject')
    inlines = [AttendanceRecordInline] # View all students for this session directly