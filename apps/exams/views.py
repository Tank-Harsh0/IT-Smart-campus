from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Exam

def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def exam_list(request):
    exams = Exam.objects.all().order_by('-start_date')
    return render(request, 'exams/exam_list.html', {'exams': exams})

@login_required
@user_passes_test(is_admin)
def create_exam(request):
    if request.method == "POST":
        name = request.POST.get('name')
        exam_type = request.POST.get('exam_type')
        semester = request.POST.get('semester')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not name or not start_date or not end_date:
            messages.error(request, "All fields are required.")
            return redirect('create_exam')

        Exam.objects.create(
            name=name,
            exam_type=exam_type,
            semester=semester,
            start_date=start_date,
            end_date=end_date
        )
        
        messages.success(request, "Exam scheduled successfully!")
        return redirect('exam_list')

    return render(request, 'exams/create_exam.html')