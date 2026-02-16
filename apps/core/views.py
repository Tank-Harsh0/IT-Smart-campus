import logging
import csv
import io
import random
import string
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from .forms import ManualTimetableForm, ManualBatchForm
from .utils import send_welcome_email
from apps.accounts.models import User
from apps.students.models import Student
from apps.faculty.models import Faculty
from apps.subjects.models import Subject
from apps.notifications.models import Notification
from apps.core.models import Classroom, Batch, TimetableSlot

logger = logging.getLogger(__name__)


# =========================
# Helpers
# =========================
# =========================
# Landing Page (Index)
# =========================
def index(request):
    # 1. If user is logged in, redirect to their specific dashboard
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        elif hasattr(request.user, 'student_profile'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'faculty_profile'):
            return redirect('faculty_dashboard')
    
    # 2. If not logged in, show the Landing Page with public notices (audience=ALL)
    public_notices = Notification.objects.filter(audience='ALL').order_by('-created_at')[:5]
    
    return render(request, 'index.html', {
        'public_notices': public_notices,
    })

# =========================
# Public Pages (No Login Required)
# =========================
def faculty_public(request):
    # Load all faculty members with their user data
    faculty_list = Faculty.objects.select_related('user').all()
    faculty_count = faculty_list.count()
    
    # Calculate average experience from dept_joining_date
    from django.utils import timezone
    from django.db.models import Avg
    today = timezone.now().date()
    
    total_years = 0
    faculty_with_dates = 0
    for f in faculty_list:
        if f.dept_joining_date:
            years = (today - f.dept_joining_date).days / 365
            total_years += years
            faculty_with_dates += 1
    
    avg_experience = round(total_years / faculty_with_dates) if faculty_with_dates > 0 else 0
    
    # Calculate teacher ratio (students per faculty)
    student_count = Student.objects.count()
    teacher_ratio = f"1:{round(student_count / faculty_count)}" if faculty_count > 0 else "N/A"
    
    return render(request, 'core/faculty_public.html', {
        'faculty_list': faculty_list,
        'avg_experience': avg_experience,
        'teacher_ratio': teacher_ratio,
    })

def curriculum(request):
    # Group subjects by semester for display
    subjects_by_semester = {}
    for sem in range(1, 7):  # Semester 1-6
        subjects_by_semester[sem] = Subject.objects.filter(semester=sem).order_by('code')
    
    return render(request, 'core/curriculum.html', {
        'subjects_by_semester': subjects_by_semester,
    })

def gallery(request):
    return render(request, 'core/gallery.html')

def is_admin(user):
    return user.is_superuser

def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# =========================
# Admin Dashboard
# =========================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    context = {
        'total_students': User.objects.filter(role=User.Role.STUDENT).count(),
        'total_faculty': User.objects.filter(role=User.Role.FACULTY).count(),
        'total_subjects': Subject.objects.count(),
        'recent_users': User.objects.order_by('-date_joined')[:5],
    }
    return render(request, 'core/admin_dashboard.html', context)


# =========================
# Bulk Upload Users (CSV)
# =========================

@login_required
@user_passes_test(is_admin)
def upload_students(request):
    if request.method == "POST":
        if 'file' not in request.FILES:
            messages.error(request, "Please select a CSV file.")
            return redirect('upload_students')

        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Only CSV files are allowed.")
            return redirect('upload_students')

        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))

            success = 0
            errors = []

            for row_no, row in enumerate(reader, start=2):
                try:
                    with transaction.atomic():
                        username = row.get('username', '').strip()
                        email = row.get('email', '').strip()
                        role_str = row.get('role', '').upper().strip()
                        first_name = row.get('first_name', '').strip()
                        last_name = row.get('last_name', '').strip()

                        if not username or not email or not role_str:
                            raise ValueError("Missing required fields")

                        if User.objects.filter(username=username).exists():
                            raise ValueError("User already exists")

                        role_map = {'STUDENT': User.Role.STUDENT, 'FACULTY': User.Role.FACULTY}
                        role = role_map.get(role_str)
                        if not role: raise ValueError("Invalid role")

                        temp_password = generate_temp_password()
                        user = User.objects.create_user(
                            username=username, email=email, password=temp_password,
                            role=role, first_name=first_name, last_name=last_name,
                            must_change_password=True
                        )

                        if role == User.Role.STUDENT:
                            Student.objects.create(user=user, enrollment_number=username, semester=1)
                        elif role == User.Role.FACULTY:
                            Faculty.objects.create(user=user, employee_id=username, designation="Lecturer", qualification="M.E.")

                        # Send welcome email with credentials
                        send_welcome_email(user, temp_password)

                        success += 1
                except Exception as e:
                    errors.append(f"Row {row_no}: {e}")

            if success: messages.success(request, f"{success} users created successfully.")
            for err in errors: messages.warning(request, err)
            return redirect('admin_dashboard')

        except Exception as e:
            logger.error(f"File processing error in upload_students: {e}")
            messages.error(request, f"File processing error: {e}")
            return redirect('upload_students')

    return render(request, 'core/Upload_student.html')


# =========================
# Bulk Upload Subjects (CSV)
# =========================

@login_required
@user_passes_test(is_admin)
def upload_subjects(request):
    if request.method == "POST":
        if 'file' not in request.FILES:
            messages.error(request, "Please select a CSV file.")
            return redirect('upload_subjects')

        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Only CSV files are allowed.")
            return redirect('upload_subjects')

        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            count = 0
            for row in reader:
                try:
                    Subject.objects.get_or_create(
                        code=row['code'].strip(),
                        defaults={'name': row['name'].strip(), 'semester': int(row['semester'])}
                    )
                    count += 1
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping row in subject upload: {e}")
                    continue

            messages.success(request, f"{count} subjects processed.")
            return redirect('admin_dashboard')
        except Exception as e:
            logger.error(f"File error in upload_subjects: {e}")
            messages.error(request, f"File error: {e}")
            return redirect('upload_subjects')

    return render(request, 'core/Upload_subjects.html')


# =========================
# List Views
# =========================

@login_required
@user_passes_test(is_admin)
def student_list(request):
    users = User.objects.filter(role=User.Role.STUDENT).order_by('first_name')
    return render(request, 'core/students.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def faculty_list(request):
    users = User.objects.filter(role=User.Role.FACULTY).order_by('first_name')
    return render(request, 'core/faculty.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def subject_list(request):
    subjects = Subject.objects.order_by('semester', 'code')
    return render(request, 'core/subjects.html', {'subjects': subjects})


# =========================
# Download Samples
# =========================

@login_required
@user_passes_test(is_admin)
def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv', headers={'Content-Disposition': 'attachment; filename="sample_users.csv"'})
    writer = csv.writer(response)
    writer.writerow(['username', 'email', 'role', 'first_name', 'last_name'])
    writer.writerow(['it001', 'it001@rcti.edu', 'STUDENT', 'Harsh', 'Patel'])
    writer.writerow(['fac001', 'fac001@rcti.edu', 'FACULTY', 'Amit', 'Verma'])
    return response

@login_required
@user_passes_test(is_admin)
def download_sample_subjects_csv(request):
    response = HttpResponse(content_type='text/csv', headers={'Content-Disposition': 'attachment; filename="sample_subjects.csv"'})
    writer = csv.writer(response)
    writer.writerow(['name', 'code', 'semester', 'credits'])
    writer.writerow(['Python Programming', '3361601', '6', '5'])
    return response



# =========================
# Upload Timetable (PDF) - ZERO WORK MODE
# =========================

@login_required
@user_passes_test(is_admin)
def upload_timetable(request):
    if request.method == 'POST':
        form = ManualTimetableForm(request.POST)
        
        if form.is_valid():
            try:
                # Extract clean data
                slot_type = form.cleaned_data['slot_type']
                classroom = form.cleaned_data['classroom']
                day = form.cleaned_data['day']
                start = form.cleaned_data['start_time']
                end = form.cleaned_data['end_time']
                subject = form.cleaned_data['subject']
                faculty = form.cleaned_data['faculty']
                room = form.cleaned_data['room_number']

                # 1. Double Booking Check
                if TimetableSlot.objects.filter(day=day, start_time=start, faculty=faculty).exists():
                    messages.error(request, f"Error: {faculty} is already teaching at {start} on {day}!")
                    return render(request, 'core/upload_timetable.html', {'form': form})

                # 2. Determine Batch
                if slot_type == 'LECTURE':
                    # Auto-create class batch (e.g. "IT6-ALL")
                    batch_name = f"{classroom.name}-ALL"
                    batch, _ = Batch.objects.get_or_create(name=batch_name, defaults={'classroom': classroom})
                else:
                    batch = form.cleaned_data['specific_batch']

                # 3. Save Slot
                TimetableSlot.objects.create(
                    day=day, start_time=start, end_time=end,
                    batch=batch, subject=subject, faculty=faculty, room_number=room
                )

                messages.success(request, f"Successfully added {slot_type} for {batch.name}")
                return redirect('upload_timetable')

            except Exception as e:
                messages.error(request, f"Database Error: {e}")
        else:
            # If form is invalid, errors will show in the template automatically
            messages.error(request, "Please fix the errors highlighted below.")
    else:
        form = ManualTimetableForm()

    return render(request, 'core/upload_timetable.html', {'form': form})


# ... keep upload_batches ...
@login_required
@user_passes_test(is_admin)
def upload_batches(request):
    if request.method == 'POST':
        form = ManualBatchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Batch '{form.cleaned_data['name']}' created successfully!")
            return redirect('upload_batches')
    else:
        form = ManualBatchForm()

    return render(request, 'core/upload_batches.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def auto_generate_batches(request):
    classrooms = Classroom.objects.all()
    created_count = 0
    
    for classroom in classrooms:
        # We want 3 batches per class: 1, 2, 3
        for i in range(1, 4):
            # Name Logic: ClassName + Number (e.g. IT11 + 1 = IT111)
            batch_name = f"{classroom.name}{i}"
            
            # Create Batch if it doesn't exist
            _, created = Batch.objects.get_or_create(
                name=batch_name,
                defaults={'classroom': classroom}
            )
            
            if created:
                created_count += 1

    messages.success(request, f"Success! Automatically created {created_count} new batches.")
    return redirect('upload_batches')

def load_subjects(request):
    semester = request.GET.get('semester')
    subjects = Subject.objects.filter(semester=semester).values('id', 'name', 'code')
    return JsonResponse(list(subjects), safe=False)

def load_classrooms(request):
    semester = request.GET.get('semester')
    # Fetch classrooms matching the semester
    classrooms = Classroom.objects.filter(semester=semester).values('id', 'name')
    return JsonResponse(list(classrooms), safe=False)
def load_batches(request):
    classroom_id = request.GET.get('classroom_id')
    batches = Batch.objects.filter(classroom_id=classroom_id).values('id', 'name')
    return JsonResponse(list(batches), safe=False)