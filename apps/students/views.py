from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from apps.accounts.decorators import student_required
from apps.assignments.models import Assignment
from apps.subjects.models import Subject
from apps.notifications.models import Notification
from apps.core.models import TimetableSlot 
from apps.students.forms import FaceRegistrationForm
from apps.attendance.models import FaceData, AttendanceRecord, AttendanceSession
import face_recognition


@login_required
@student_required
def attendance_stats(request):
    student = request.user.student_profile

    subjects = Subject.objects.filter(semester=student.semester).annotate(
        total_sessions=Count('attendancesession', distinct=True),
        present_sessions=Count(
            'attendancesession__records',
            filter=Q(
                attendancesession__records__student=student,
                attendancesession__records__is_present=True,
            ),
            distinct=True,
        ),
    )

    total_classes = sum(sub.total_sessions for sub in subjects)
    present_count = sum(sub.present_sessions for sub in subjects)
    absent_count = total_classes - present_count
    
    percentage = 0
    degrees = 0
    if total_classes > 0:
        percentage = int((present_count / total_classes) * 100)
        degrees = int(percentage * 3.6)

    subject_data = []
    for sub in subjects:
        sub_total = sub.total_sessions
        sub_present = sub.present_sessions
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


@login_required
@student_required
def student_dashboard(request):
    student = request.user.student_profile
    subjects = Subject.objects.filter(semester=student.semester)

    pending_assignments = Assignment.objects.filter(
        subject__semester=student.semester
    ).select_related('subject').order_by('due_date')

    for asm in pending_assignments:
        if asm.due_date < timezone.now():
            asm.status = 'Overdue'
        else:
            asm.status = 'Pending'

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


@login_required
@student_required
def assignment_list(request):
    try:
        student = request.user.student_profile
    except ObjectDoesNotExist:
        return redirect('student_dashboard')

    assignments = Assignment.objects.filter(
        subject__semester=student.semester
    ).select_related('subject').order_by('due_date')
    
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


@login_required
@student_required
def student_profile(request):
    return render(request, 'students/profile.html', {'student': request.user.student_profile})

@login_required
@student_required
def student_results(request):
    student = request.user.student_profile

    from apps.exams.models import ExamResult

    exam_results = []
    all_results = (
        ExamResult.objects.filter(
            student=student,
            exam__is_published=True,
            exam__semester=student.semester,
            marks_obtained__isnull=False,
        )
        .select_related('exam', 'subject')
        .order_by('-exam__published_at', '-exam_id', 'subject__code')
    )

    grouped = {}
    for r in all_results:
        entry = grouped.setdefault(
            r.exam_id,
            {
                'exam': r.exam,
                'subjects': [],
                'total_obtained': 0,
                'total_marks': 0,
            },
        )
        obtained = r.marks_obtained
        out_of = r.total_marks
        entry['total_obtained'] += obtained
        entry['total_marks'] += out_of
        entry['subjects'].append({
            'subject': r.subject.name,
            'code': r.subject.code,
            'marks_obtained': obtained,
            'total_marks': out_of,
            'grade': r.grade,
            'status': 'PASS' if r.is_passed else 'FAIL',
        })

    for entry in grouped.values():
        total_obtained = entry['total_obtained']
        total_marks = entry['total_marks']
        entry['overall_percentage'] = round(
            (total_obtained / total_marks) * 100, 2
        ) if total_marks > 0 else 0.00
        exam_results.append(entry)

    return render(request, 'students/results.html', {
        'student': student,
        'exam_results': exam_results,
    })




@login_required
@student_required
def student_timetable(request):
    student = request.user.student_profile
    
    my_batch = student.batch
    
    target_batches = []
    
    if my_batch:
        target_batches.append(my_batch.name)
        
        if my_batch.classroom:
            classroom_name = my_batch.classroom.name 
            lecture_batch_name = f"{classroom_name}-ALL"
            target_batches.append(lecture_batch_name)
    
    if target_batches:
        slots = list(TimetableSlot.objects.filter(
            batch__name__in=target_batches
        ).select_related('subject', 'faculty__user', 'batch').order_by('day', 'start_time'))
    else:
        slots = []

    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    grouped = {day: [] for day in days_order}
    for slot in slots:
        if slot.day in grouped:
            grouped[slot.day].append(slot)

    weekly_schedule = []
    for day in days_order:
        day_slots = grouped[day]
        weekly_schedule.append({
            'day_name': day,
            'slots': day_slots,
            'count': len(day_slots)
        })
    
    return render(request, 'students/schedule.html', {
        'student': student,
        'weekly_schedule': weekly_schedule
    })
@login_required
@student_required
def student_notifications(request):
    notifications = Notification.objects.filter(
        audience__in=['ALL', 'STUDENT']
    ).order_by('-created_at')

    return render(request, 'students/notification.html', {
        'student': request.user.student_profile,
        'notifications': notifications,
    })
