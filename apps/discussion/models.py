from django.db import models
from django.conf import settings
from apps.subjects.models import Subject


class Discussion(models.Model):
    """A discussion thread linked to a subject."""
    TAG_CHOICES = [
        ('Question', 'Question'),
        ('Doubt', 'Doubt'),
        ('Resource', 'Resource'),
        ('Announcement', 'Announcement'),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='discussions')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discussions')
    tag = models.CharField(max_length=20, choices=TAG_CHOICES, default='Question', blank=True)
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title

    @property
    def reply_count(self):
        return self.replies.count()


class Reply(models.Model):
    """A reply to a discussion thread."""
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='replies')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author} on {self.discussion.title}"
