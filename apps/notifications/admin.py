from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'priority', 'created_at')
    list_filter = ('audience', 'priority', 'created_at')
    search_fields = ('title', 'message')
    ordering = ('-created_at',)
