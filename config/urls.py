from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Smart Redirect View for Root URL
def root_redirect_view(request):
    if not request.user.is_authenticated:
        return redirect('index')
    
    # Role-based dispatch
    if request.user.is_admin:
        return redirect('admin_dashboard')
    elif request.user.is_faculty:
        return redirect('faculty_dashboard')
    elif request.user.is_student:
        return redirect('student_dashboard')
    
    return redirect('login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('core/', include('apps.core.urls')),
    path('faculty/', include('apps.faculty.urls')),
    path('student/', include('apps.students.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('exams/', include('apps.exams.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('leave/', include('apps.leave.urls')),
    path('discussion/', include('apps.discussion.urls')),
    path('ml/', include('apps.ml.urls')),

    # Base
    path('', root_redirect_view, name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)