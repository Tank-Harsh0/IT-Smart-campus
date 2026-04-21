from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from reportlab.lib import colors
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.db.models import Count
from .models import Faculty
from apps.accounts.decorators import faculty_required
from apps.subjects.models import Subject
from apps.assignments.models import Assignment
from apps.faculty.forms import AssignmentCreateForm, FacultyProfileForm
from apps.students.models import Student
from apps.notifications.models import Notification
from apps.core.models import TimetableSlot
from apps.exams.models import Exam, ExamSubject, ExamResult


@login_required
@faculty_required
def faculty_dashboard(request):
    faculty = request.user.faculty_profile
    student = Student.objects.count()
    subjects = Subject.objects.filter(faculty=faculty)

    # Recent assignments created by this faculty
    recent_assignments = Assignment.objects.filter(
        subject__faculty=faculty
    ).order_by('-created_at')[:5]

    return render(request, 'faculty/dashboard.html', {
        'faculty': faculty,
        'student': student,
        'subjects': subjects,
        'recent_assignments': recent_assignments
    })

@login_required
@faculty_required
def create_assignment(request, subject_id=None):
    faculty = request.user.faculty_profile
    
    if subject_id:
        subject = get_object_or_404(Subject, id=subject_id, faculty=faculty)
    else:
        subject = None
    
    if request.method == 'POST':
        form = AssignmentCreateForm(request.POST, request.FILES, faculty=faculty)
        if form.is_valid():
            assignment = form.save(commit=False)
            if subject:
                assignment.subject = subject
            assignment.save()
            messages.success(request, f"Assignment created for {assignment.subject.code}")
            return redirect('faculty_dashboard')
    else:
        form = AssignmentCreateForm(faculty=faculty)
    
    return render(request, 'faculty/create_assignment.html', {
        'form': form, 
        'subject': subject,
        'faculty': faculty
    })
@login_required
@faculty_required
def student_list(request):
    faculty = request.user.faculty_profile
    students = Student.objects.select_related('user', 'batch').order_by('semester', 'enrollment_number')
    return render(request, 'faculty/student_list.html', {
        'faculty': faculty,
        'students': students
    })

@login_required
@faculty_required
def faculty_schedule(request):
    faculty = request.user.faculty_profile
    
    all_slots = TimetableSlot.objects.filter(faculty=faculty).select_related('subject', 'batch').order_by('start_time')

    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    
    weekly_schedule = []
    
    for day in days_order:
        day_slots = [slot for slot in all_slots if slot.day == day]
        
        weekly_schedule.append({
            'day_name': day,
            'slots': day_slots,
            'count': len(day_slots)
        })

    return render(request, 'faculty/schedule.html', {'weekly_schedule': weekly_schedule})

@login_required
@faculty_required
def faculty_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'faculty/notifications.html', {
        'notifications': notifications
    })
@login_required
@faculty_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )
    notification.is_read = True
    notification.save()
    return redirect('faculty_notifications')

@login_required
@faculty_required
def faculty_attendance(request):
    faculty = request.user.faculty_profile
    subjects = Subject.objects.filter(faculty=faculty)
    return render(request, 'faculty/attendance.html', {
        'faculty': faculty,
        'subjects': subjects
    })

@login_required
@faculty_required
def faculty_profile(request):
    faculty = request.user.faculty_profile
    return render(request, 'faculty/profile.html', {'faculty': faculty})

@login_required
@faculty_required
def edit_faculty_profile(request):
    profile = request.user.faculty_profile

    if request.method == 'POST':
        form = FacultyProfileForm(
            request.POST,
            request.FILES,
            instance=profile
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('faculty_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FacultyProfileForm(instance=profile)

    return render(request, 'faculty/edit_profile.html', {
        'form': form
    })
@login_required
def download_schedule_pdf(request):
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        return HttpResponse("Faculty profile not found", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Schedule_{faculty.initials}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)
    elements.append(Paragraph(f"Weekly Schedule - {request.user.get_full_name()} ({faculty.initials})", title_style))
    elements.append(Spacer(1, 10))

    data = [['Day', 'Time', 'Type', 'Subject', 'Batch', 'Room']]
    
    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    slots = TimetableSlot.objects.filter(faculty=faculty).select_related('subject', 'batch')
    
    day_map = {d: i for i, d in enumerate(days_order)}
    sorted_slots = sorted(slots, key=lambda s: (day_map.get(s.day, 9), s.start_time))

    for slot in sorted_slots:
        slot_type = "Lecture" if "ALL" in slot.batch.name else "Lab"
        
        row = [
            slot.day,
            f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
            slot_type,
            slot.subject.code,
            slot.batch.name,
            slot.room_number
        ]
        data.append(row)

    table = Table(data, colWidths=[50, 90, 60, 80, 80, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))

    elements.append(table)
    
    doc.build(elements)
    return response



@login_required
@faculty_required
def faculty_exam_list(request):
    faculty = request.user.faculty_profile
    my_subject_ids = list(
        Subject.objects.filter(faculty=faculty).values_list('id', flat=True)
    )
    today = timezone.now().date()

    if not my_subject_ids:
        return render(request, 'faculty/exams.html', {'exams_with_subjects': []})

    all_exams = Exam.objects.filter(
        exam_subjects__subject_id__in=my_subject_ids,
        end_date__lte=today
    ).distinct().order_by('-end_date')

    if not all_exams:
        return render(request, 'faculty/exams.html', {'exams_with_subjects': []})

    exam_ids = list(all_exams.values_list('id', flat=True))
    semester_counts = {
        row['semester']: row['total']
        for row in (
            Student.objects.filter(
                semester__in=all_exams.values_list('semester', flat=True)
            )
            .values('semester')
            .annotate(total=Count('id'))
        )
    }
    graded_map = {
        (row['exam_id'], row['subject_id']): row['graded']
        for row in (
            ExamResult.objects.filter(
                exam_id__in=exam_ids,
                subject_id__in=my_subject_ids,
                marks_obtained__isnull=False
            )
            .values('exam_id', 'subject_id')
            .annotate(graded=Count('id'))
        )
    }
    exam_subjects = (
        ExamSubject.objects.filter(exam_id__in=exam_ids, subject_id__in=my_subject_ids)
        .select_related('subject')
        .order_by('subject__code')
    )
    subjects_by_exam = {}
    for es in exam_subjects:
        subjects_by_exam.setdefault(es.exam_id, []).append(es)

    exams_with_subjects = []
    for exam in all_exams:
        total_students = semester_counts.get(exam.semester, 0)
        subjects_info = []
        for es in subjects_by_exam.get(exam.id, []):
            graded = graded_map.get((exam.id, es.subject_id), 0)
            subjects_info.append({
                'exam_subject': es,
                'graded': graded,
                'total': total_students,
                'complete': graded == total_students and total_students > 0,
            })

        exams_with_subjects.append({
            'exam': exam,
            'subjects': subjects_info,
        })

    return render(request, 'faculty/exams.html', {
        'exams_with_subjects': exams_with_subjects,
    })



@login_required
@faculty_required
def faculty_grade_exam(request, exam_id, subject_id):
    faculty = request.user.faculty_profile
    exam = get_object_or_404(Exam, id=exam_id)
    subject = get_object_or_404(Subject, id=subject_id, faculty=faculty)
    exam_subject = get_object_or_404(ExamSubject, exam=exam, subject=subject)

    students = Student.objects.filter(semester=exam.semester).order_by('enrollment_number')

    if request.method == 'POST':
        graded_count = 0
        for student in students:
            marks_val = request.POST.get(f'marks_{student.id}', '').strip()
            if marks_val:
                try:
                    marks = int(marks_val)
                    if marks < 0 or marks > exam_subject.total_marks:
                        continue
                    ExamResult.objects.update_or_create(
                        exam=exam,
                        subject=subject,
                        student=student,
                        defaults={
                            'marks_obtained': marks,
                            'total_marks': exam_subject.total_marks,
                            'graded_by': faculty,
                            'graded_at': timezone.now(),
                        }
                    )
                    graded_count += 1
                except (ValueError, TypeError):
                    continue

        messages.success(request, f"Graded {graded_count} students for {subject.code}!")
        return redirect('faculty_exam_list')

    existing_results = {}
    for er in ExamResult.objects.filter(exam=exam, subject=subject):
        existing_results[er.student_id] = er.marks_obtained

    student_data = []
    for student in students:
        student_data.append({
            'student': student,
            'existing_marks': existing_results.get(student.id, ''),
        })

    return render(request, 'faculty/grade_exam.html', {
        'exam': exam,
        'subject': subject,
        'exam_subject': exam_subject,
        'student_data': student_data,
    })
