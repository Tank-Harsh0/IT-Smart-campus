from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from reportlab.lib import colors
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from .models import Faculty
from apps.accounts.decorators import faculty_required
from apps.subjects.models import Subject
from apps.assignments.models import Assignment
from apps.faculty.forms import AssignmentCreateForm, FacultyProfileForm
from apps.students.models import Student
from apps.notifications.models import Notification
from apps.core.models import TimetableSlot

@login_required
@faculty_required
def faculty_dashboard(request):
    faculty = request.user.faculty_profile
    student = Student.objects.all().count()
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
    
    # If subject_id is provided, use that subject
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
    # Get all students sorted by semester
    students = Student.objects.all().order_by('semester', 'enrollment_number')
    return render(request, 'faculty/student_list.html', {
        'faculty': faculty,
        'students': students
    })

@login_required
@faculty_required
def faculty_schedule(request):
    faculty = request.user.faculty_profile
    
    # Fetch all slots for this faculty, sorted by time
    all_slots = TimetableSlot.objects.filter(faculty=faculty).order_by('start_time')

    # Define the order of days
    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    
    # Transform data into a LIST of dictionaries for the template
    # We use the variable name 'weekly_schedule' to match the HTML template
    weekly_schedule = []
    
    for day in days_order:
        # Get slots for this specific day
        day_slots = [slot for slot in all_slots if slot.day == day]
        
        # Append to the list with the exact keys the template needs
        weekly_schedule.append({
            'day_name': day,       # Used for the header (e.g., "MON")
            'slots': day_slots,    # Used for the loop of classes
            'count': len(day_slots) # Used for the "X Classes" badge
        })

    # Pass the list to the template using the correct key 'weekly_schedule'
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
    # 1. Get Faculty Profile
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        return HttpResponse("Faculty profile not found", status=404)

    # 2. Setup PDF Response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Schedule_{faculty.initials}.pdf"'

    # 3. Create PDF Document
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # 4. Title & Header
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)
    elements.append(Paragraph(f"Weekly Schedule - {request.user.get_full_name()} ({faculty.initials})", title_style))
    elements.append(Spacer(1, 10))

    # 5. Prepare Table Data
    # Headers
    data = [['Day', 'Time', 'Type', 'Subject', 'Batch', 'Room']]
    
    # Content
    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    slots = TimetableSlot.objects.filter(faculty=faculty)
    
    # Sort by Day then Time
    # (We map MON->0, TUE->1 for sorting)
    day_map = {d: i for i, d in enumerate(days_order)}
    sorted_slots = sorted(slots, key=lambda s: (day_map.get(s.day, 9), s.start_time))

    for slot in sorted_slots:
        # Determine Type based on Batch Name
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

    # 6. Style the Table
    table = Table(data, colWidths=[50, 90, 60, 80, 80, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')), # Header Dark Blue
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')), # Rows Light Gray
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))

    elements.append(table)
    
    # 7. Build
    doc.build(elements)
    return response