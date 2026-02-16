#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements-deploy.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create demo data automatically
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()

# --- Admin ---
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@rcti.edu', 'Admin@123')
    user.role = 'ADMIN'
    user.save()
    print('Created admin: admin / Admin@123')

# --- Faculty ---
if not User.objects.filter(username='faculty1').exists():
    fuser = User(
        username='faculty1',
        email='faculty1@rcti.edu',
        first_name='Ketan',
        last_name='Patel',
        role='FACULTY',
    )
    fuser.set_password('Faculty@123')
    fuser.save()

    from apps.faculty.models import Faculty
    faculty = Faculty.objects.create(
        user=fuser,
        employee_id='FAC001',
        designation='Assistant Professor',
        qualification='M.E. Computer Engineering',
        initials='KKP',
    )
    print('Created faculty: faculty1 / Faculty@123')

    # --- Subject assigned to faculty ---
    from apps.subjects.models import Subject
    Subject.objects.get_or_create(
        code='IT503',
        defaults={
            'name': 'Python Programming',
            'semester': 5,
            'faculty': faculty,
        }
    )
    Subject.objects.get_or_create(
        code='IT504',
        defaults={
            'name': 'Web Technology',
            'semester': 5,
            'faculty': faculty,
        }
    )
    print('Created subjects: IT503, IT504')
else:
    print('Faculty already exists')

# --- Student ---
if not User.objects.filter(username='student1').exists():
    suser = User(
        username='student1',
        email='student1@rcti.edu',
        first_name='Harsh',
        last_name='Tank',
        role='STUDENT',
    )
    suser.set_password('Student@123')
    suser.save()

    from apps.core.models import Classroom, Batch
    classroom, _ = Classroom.objects.get_or_create(name='IT61', defaults={'semester': 5})
    batch, _ = Batch.objects.get_or_create(name='IT61-ALL', defaults={'classroom': classroom})

    from apps.students.models import Student
    Student.objects.create(
        user=suser,
        enrollment_number='22IT121',
        semester=5,
        batch=batch,
    )
    print('Created student: student1 / Student@123')
else:
    print('Student already exists')

print('--- Demo data setup complete ---')
EOF
