from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from apps.accounts.decorators import student_required
from apps.assignments.models import Assignment
from apps.subjects.models import Subject
from apps.notifications.models import Notification
from apps.core.models import TimetableSlot 
from apps.students.forms import FaceRegistrationForm
from apps.attendance.models import FaceData, AttendanceRecord, AttendanceSession
from apps.students.models import Result
import face_recognition

# ==========================================
# 1. ATTENDANCE STATS
# ==========================================
@login_required
@student_required
def attendance_stats(request):
    student = request.user.student_profile
    
    # 1. Total records for this student
    subjects = Subject.objects.filter(semester=student.semester)
    total_classes = AttendanceSession.objects.filter(subject__in=subjects).count()
    present_count = AttendanceRecord.objects.filter(student=student, is_present=True).count()
    absent_count = total_classes - present_count
    
    percentage = 0
    degrees = 0
    if total_classes > 0:
        percentage = int((present_count / total_classes) * 100)
        degrees = int(percentage * 3.6)

    # 2. Subject-wise breakdown
    subject_data = []
    for sub in subjects:
        sub_total = AttendanceSession.objects.filter(subject=sub).count()
        sub_present = AttendanceRecord.objects.filter(session__subject=sub, student=student, is_present=True).count()
        sub_percent = 0
        if sub_total > 0:
            sub_percent = int((sub_present / sub_total) * 100)
            
        subject_data.append({
            'name': sub.name,
            'code': sub.code,
            'total': sub_total,
            'present': sub_present,
            'percentage': sub_percent
        })

    context = {
        'student': student,
        'percentage': percentage,
        'degrees': str(degrees) + 'deg',
        'present_count': present_count,
        'absent_count': absent_count,
        'subject_data': subject_data
    }
    return render(request, 'students/attendance_stats.html', context)

# ==========================================
# 2. FACE REGISTRATION
# ==========================================
@login_required
@student_required
def register_face_view(request):
    student = request.user.student_profile
    existing_face = FaceData.objects.filter(student=student).first()

    if request.method == 'POST':
        form = FaceRegistrationForm(request.POST, request.FILES, instance=existing_face)
        if form.is_valid():
            try:
                uploaded_image = request.FILES['face_image']
                image = face_recognition.load_image_file(uploaded_image)
                encodings = face_recognition.face_encodings(image)
                
                if len(encodings) == 0:
                    messages.error(request, "No face detected. Try again.")
                elif len(encodings) > 1:
                    messages.error(request, "Multiple faces detected. Upload a solo photo.")
                else:
                    face_instance = form.save(commit=False)
                    face_instance.student = student
                    face_instance.set_encoding(encodings[0])
                    face_instance.save()
                    messages.success(request, "Face ID registered successfully!")
                    return redirect('student_dashboard')

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
    else:
        form = FaceRegistrationForm(instance=existing_face)

    return render(request, 'students/register_face.html', {
        'student': student, 'form': form, 'existing_face': existing_face
    })

# ==========================================
# 3. STUDENT DASHBOARD (Fixed Assignments)
# ==========================================
@login_required
@student_required
def student_dashboard(request):
    student = request.user.student_profile
    subjects = Subject.objects.filter(semester=student.semester)

    # 1. Fetch Assignments
    pending_assignments = Assignment.objects.filter(
        subject__semester=student.semester
    ).order_by('due_date')

    # 2. Calculate Status (REMOVED Submission Logic)
    for asm in pending_assignments:
        # Simple Logic: If date passed -> Overdue, else Pending
        if asm.due_date < timezone.now():
            asm.status = 'Overdue'
        else:
            asm.status = 'Pending'

    # 3. Attendance Stats
    total_sessions = AttendanceSession.objects.filter(subject__in=subjects).count()
    present_count = AttendanceRecord.objects.filter(student=student, is_present=True).count()
    
    attendance_percentage = 0
    attendance_degrees = 0
    if total_sessions > 0:
        attendance_percentage = int((present_count / total_sessions) * 100)
        attendance_degrees = int(attendance_percentage * 3.6)

    context = {
        'student': student,
        'subjects': subjects,
        'pending_assignments': pending_assignments,
        'attendance_percentage': attendance_percentage,
        'attendance_degrees': str(attendance_degrees) + 'deg',
    }
    return render(request, 'students/dashboard.html', context)

# ==========================================
# 4. ASSIGNMENT LIST (Fixed)
# ==========================================
@login_required
@student_required
def assignment_list(request):
    try:
        student = request.user.student_profile
    except ObjectDoesNotExist:
        return redirect('student_dashboard')

    assignments = Assignment.objects.filter(subject__semester=student.semester).order_by('due_date')
    
    pending_count = 0
    
    for asm in assignments:
        if asm.due_date < timezone.now():
            asm.status = "Overdue"
            pending_count += 1
        else:
            asm.status = "Pending"
            pending_count += 1
        
    return render(request, 'students/assignment_list.html', {
        'student': student,
        'assignments': assignments,
        'submitted_count': 0,
        'pending_count': pending_count
    })

# ==========================================
# 5. PROFILE & RESULTS
# ==========================================
@login_required
@student_required
def student_profile(request):
    return render(request, 'students/profile.html', {'student': request.user.student_profile})

@login_required
@student_required
def student_results(request):
    student = request.user.student_profile
    results = Result.objects.filter(student=student).select_related('subject')
    
    total_credits = 0
    total_weighted_points = 0
    processed_results = []
    
    for res in results:
        points = res.calculate_points()
        total_credits += res.credits
        total_weighted_points += (points * res.credits)
        processed_results.append({
            'subject': res.subject.name,
            'code': res.subject.code,
            'grade': res.grade,
            'points': points,
            'status': 'PASS' if res.is_passed() else 'FAIL'
        })

    spi = round(total_weighted_points / total_credits, 2) if total_credits > 0 else 0.00
    return render(request, 'students/results.html', {
        'student': student, 'results': processed_results, 'spi': spi, 'cgpa': spi
    })

# ==========================================
# 6. TIMETABLE (Updated to TimetableSlot)
# ==========================================
@login_required
@student_required
def student_timetable(request):
    student = request.user.student_profile
    
    # 1. Identify Batches (Safe Check)
    my_batch = student.batch # This might be None
    
    target_batches = []
    
    if my_batch:
        # Add the student's specific lab batch (e.g., IT611)
        target_batches.append(my_batch.name)
        
        # Add the whole class lecture batch (e.g., IT61-ALL)
        if my_batch.classroom:
            classroom_name = my_batch.classroom.name 
            lecture_batch_name = f"{classroom_name}-ALL"
            target_batches.append(lecture_batch_name)
    
    # 2. Fetch Slots (Only if batches exist)
    if target_batches:
        slots = TimetableSlot.objects.filter(
            batch__name__in=target_batches
        ).select_related('subject', 'faculty', 'batch').order_by('start_time')
    else:
        # Return empty list if no batch assigned
        slots = TimetableSlot.objects.none()

    # 3. Group by Day
    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    weekly_schedule = []

    for day in days_order:
        day_slots = slots.filter(day=day)
        weekly_schedule.append({
            'day_name': day,
            'slots': day_slots,
            'count': day_slots.count()
        })
    
    return render(request, 'students/schedule.html', {
        'student': student,
        'weekly_schedule': weekly_schedule
    })
@login_required
@student_required
def student_notifications(request):
    # Fetch notifications targeted at ALL users or specifically STUDENTS
    # Ordered by newest first
    notifications = Notification.objects.filter(
        audience__in=['ALL', 'STUDENT']
    ).order_by('-created_at')

    return render(request, 'students/notification.html', {
        'student': request.user.student_profile,
        'notifications': notifications,
    })