import re
import csv
import io
import random
import string
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
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

def faculty_detail(request, pk):
    """Public faculty profile detail page"""
    from django.shortcuts import get_object_or_404
    faculty = get_object_or_404(Faculty.objects.select_related('user'), pk=pk)
    return render(request, 'core/faculty_detail.html', {
        'faculty': faculty,
    })

def is_admin(user):
    return user.is_superuser

def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_semester_from_string(text):
    """
    Extracts semester based on IT code.
    IT1... -> 1, IT3... -> 3, IT5... -> 5
    """
    match = re.search(r'IT(\d)', text)
    if match:
        return int(match.group(1))
    return 1  # Default

def fix_time_format(t_str):
    """
    Converts 1:00 -> 13:00 (PM logic) if hour is between 1 and 6.
    """
    t_str = t_str.replace('.', ':')
    try:
        t_obj = datetime.strptime(t_str, "%H:%M")
        if 1 <= t_obj.hour <= 6:
            t_obj = t_obj.replace(hour=t_obj.hour + 12)
        return t_obj.strftime("%H:%M")
    except ValueError:
        return t_str

def expand_enrollment_range(text):
    """
    Expands '201 to 205' into ['201', '202', '203', '204', '205']
    """
    enrollments = []
    parts = re.split(r',| and ', text)
    
    for part in parts:
        part = part.strip()
        if ' to ' in part:
            try:
                start_s, end_s = part.split(' to ')
                start = int(start_s.strip())
                end = int(end_s.strip())
                enrollments.extend([str(i) for i in range(start, end + 1)])
            except ValueError:
                continue
        else:
            clean_num = re.sub(r'\D', '', part)
            if clean_num:
                enrollments.append(clean_num)
    return enrollments


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
def Upload_students(request):
    if request.method == "POST":
        if 'file' not in request.FILES:
            messages.error(request, "Please select a CSV file.")
            return redirect('Upload_students')

        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Only CSV files are allowed.")
            return redirect('Upload_students')

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
            messages.error(request, f"File processing error: {e}")
            return redirect('Upload_students')

    return render(request, 'core/Upload_student.html')


# =========================
# Bulk Upload Subjects (CSV)
# =========================

@login_required
@user_passes_test(is_admin)
def Upload_subjects(request):
    if request.method == "POST":
        if 'file' not in request.FILES:
            messages.error(request, "Please select a CSV file.")
            return redirect('Upload_subjects')

        csv_file = request.FILES['file']
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
                except Exception: continue

            messages.success(request, f"{count} subjects processed.")
            return redirect('admin_dashboard')
        except Exception as e:
            messages.error(request, f"File error: {e}")
            return redirect('Upload_subjects')

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
def Faculty_list(request):
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
# Upload Batches (PDF)
# =========================

@login_required
@user_passes_test(is_admin)
def upload_timetable(request):
    # Case 1: Form Submitted
    if request.method == 'POST':
        form = ManualTimetableForm(request.POST)
        if form.is_valid():
            try:
                slot_type = form.cleaned_data['slot_type']
                classroom = form.cleaned_data['classroom']
                
                # Determine Batch (Lecture = All, Lab = Specific)
                if slot_type == 'LECTURE':
                    # Auto-create the "-ALL" batch if it doesn't exist
                    batch_name = f"{classroom.name}-ALL"
                    batch, _ = Batch.objects.get_or_create(name=batch_name, defaults={'classroom': classroom})
                else:
                    batch = form.cleaned_data['specific_batch']

                # Create Slot
                TimetableSlot.objects.create(
                    day=form.cleaned_data['day'],
                    start_time=form.cleaned_data['start_time'],
                    end_time=form.cleaned_data['end_time'],
                    batch=batch,
                    subject=form.cleaned_data['subject'],
                    faculty=form.cleaned_data['faculty'],
                    room_number=form.cleaned_data['room_number']
                )
                
                messages.success(request, f"Successfully added {slot_type} for {batch.name}")
                return redirect('upload_timetable')

            except Exception as e:
                messages.error(request, f"Database Error: {e}")
        else:
            # --- DEBUGGING: PRINT ERRORS TO TERMINAL ---
            print("FORM ERRORS:", form.errors)
            messages.error(request, "Please correct the errors highlighted below.")
            
    # Case 2: Load Empty Form
    else:
        form = ManualTimetableForm()

    return render(request, 'core/upload_timetable.html', {'form': form})

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
# =========================
# DB Save Helper - THE MAGIC IS HERE
# =========================

def save_slot(day, start, end, match_data, is_lab, class_name, semester):
    try:
        if is_lab:
            subj_code, batch_name, faculty_initial, room = match_data
        else:
            subj_code, faculty_initial, room = match_data
            batch_name = f"{class_name}-ALL"

        # 1. Subject (Get or Create)
        subject, _ = Subject.objects.get_or_create(
            code=subj_code, 
            defaults={'name': subj_code, 'semester': semester}
        )

        # 2. Classroom & Batch (Get or Create)
        classroom, _ = Classroom.objects.get_or_create(
            name=class_name, 
            defaults={'semester': semester}
        )
        batch, _ = Batch.objects.get_or_create(
            name=batch_name, 
            defaults={'classroom': classroom}
        )

        # 3. Faculty (AUTO-CREATE IF MISSING)
        faculty = Faculty.objects.filter(initials__iexact=faculty_initial).first()
        
        if not faculty:
            # --- AUTO-GENERATION LOGIC ---
            # Create a placeholder user and faculty profile automatically
            # so you don't have to manually register them.
            clean_initial = faculty_initial.strip().upper()
            dummy_username = f"fac_{clean_initial.lower()}_{random.randint(100,999)}"
            dummy_password = "password123"
            
            user = User.objects.create_user(
                username=dummy_username, 
                password=dummy_password, 
                role=User.Role.FACULTY,
                first_name=f"Faculty {clean_initial}",
                last_name="AutoGenerated"
            )
            faculty = Faculty.objects.create(
                user=user,
                initials=clean_initial,
                employee_id=dummy_username,
                designation="Lecturer (Auto)"
            )
            print(f"Auto-created Faculty: {clean_initial}")

        # 4. Create or Update Slot (NO DUPLICATES)
        # update_or_create ensures that if you re-upload, it updates instead of crashing
        TimetableSlot.objects.update_or_create(
            day=day,
            start_time=start,
            faculty=faculty, # Unique constraint check
            defaults={
                'end_time': end,
                'batch': batch,
                'subject': subject,
                'room_number': room
            }
        )
        print(f"Upserted: {day} {start} | {subj_code} | {faculty_initial}")

    except Exception as e:
        print(f"Failed to save slot: {e}")

# Add these imports if missing
from .models import Classroom, Batch

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