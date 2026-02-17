from django.contrib import admin
from .models import Discussion, Reply


class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 0


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'author', 'is_pinned', 'is_closed', 'created_at')
    list_filter = ('is_pinned', 'is_closed', 'subject')
    search_fields = ('title', 'body')
    inlines = [ReplyInline]


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'author', 'created_at')
