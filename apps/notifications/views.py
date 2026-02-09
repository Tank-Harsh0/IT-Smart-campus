from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Notification

def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def send_notification(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        audience = request.POST.get('audience')
        priority = request.POST.get('priority')

        if not title or not message:
            messages.error(request, "Title and Message are required.")
            return redirect('send_notification')

        Notification.objects.create(
            title=title,
            message=message,
            audience=audience,
            priority=priority
        )
        
        messages.success(request, "Notification broadcasted successfully!")
        return redirect('send_notification')

    # Fetch recent history for the sidebar/log
    recent_notifications = Notification.objects.order_by('-created_at')[:10]
    
    return render(request, 'notifications/send_notification.html', {
        'recent_notifications': recent_notifications
    })