from django.contrib import admin
from apps.core.models import Classroom, Batch, TimetableSlot

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester')
    search_fields = ('name',)

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'classroom')
    list_filter = ('classroom',)
    search_fields = ('name',)

@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    # Columns to show in the list view
    list_display = ('day', 'start_time', 'subject', 'batch', 'faculty', 'room_number')
    
    # Filters on the right side
    list_filter = ('day', 'batch__classroom', 'faculty')
    
    # Search bar (Search by Faculty Name or Batch)
    search_fields = ('faculty__user__first_name', 'faculty__initials', 'batch__name', 'subject__name')
    
    # Enable sorting by time
    ordering = ('day', 'start_time')