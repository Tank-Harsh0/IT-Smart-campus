import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import Exam, ExamSubject, ExamResult, ExamSchedule
from apps.subjects.models import Subject
from apps.students.models import Student

logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_superuser


# ===========================
# ADMIN: Exam List
# ===========================
@login_required
@user_passes_test(is_admin)
def exam_list(request):
    exams = Exam.objects.all().order_by('-start_date')
    return render(request, 'exams/exam_list.html', {'exams': exams})


# ===========================
# ADMIN: Create Exam
# ===========================
@login_required
@user_passes_test(is_admin)
def create_exam(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        exam_type = request.POST.get('exam_type', 'MID')
        semester = request.POST.get('semester')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not name or not start_date or not end_date or not semester:
            messages.error(request, "All fields are required.")
            return redirect('create_exam')

        # Create exam
        exam = Exam.objects.create(
            name=name,
            exam_type=exam_type,
            semester=int(semester),
            start_date=start_date,
            end_date=end_date
        )

        # Add subjects with marks
        subject_ids = request.POST.getlist('subjects')
        for sid in subject_ids:
            marks = request.POST.get(f'marks_{sid}', '20')
            try:
                subject = Subject.objects.get(id=sid)
                ExamSubject.objects.create(
                    exam=exam,
                    subject=subject,
                    total_marks=int(marks) if marks else 20
                )
            except (Subject.DoesNotExist, ValueError) as e:
                logger.warning(f"Skipping subject {sid}: {e}")

        messages.success(request, f"Exam '{exam.name}' created with {len(subject_ids)} subjects!")
        return redirect('exam_detail', exam_id=exam.id)

    # GET: load subjects for template
    subjects_by_semester = {}
    for sem in range(1, 7):
        subjects_by_semester[sem] = list(
            Subject.objects.filter(semester=sem).order_by('code').values('id', 'name', 'code')
        )

    return render(request, 'exams/create_exam.html', {
        'subjects_by_semester': json.dumps(subjects_by_semester),
    })


# ===========================
# ADMIN: Exam Detail
# ===========================
@login_required
@user_passes_test(is_admin)
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam_subjects = exam.exam_subjects.select_related('subject').all()

    # Build subject-wise grading progress
    subject_progress = []
    total_students = Student.objects.filter(semester=exam.semester).count()

    for es in exam_subjects:
        graded = ExamResult.objects.filter(
            exam=exam, subject=es.subject, marks_obtained__isnull=False
        ).count()
        # Check if schedule exists
        schedule = getattr(es, 'schedule', None)
        try:
            schedule = es.schedule
        except ExamSchedule.DoesNotExist:
            schedule = None

        subject_progress.append({
            'subject': es.subject,
            'total_marks': es.total_marks,
            'graded': graded,
            'total': total_students,
            'percent': round((graded / total_students) * 100) if total_students > 0 else 0,
            'schedule': schedule,
        })

    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'subject_progress': subject_progress,
        'total_students': total_students,
    })


# ===========================
# ADMIN: Publish / Unpublish
# ===========================
@login_required
@user_passes_test(is_admin)
def publish_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam.is_published = True
    exam.published_at = timezone.now()
    exam.save()
    messages.success(request, f"Results for '{exam.name}' have been published!")
    return redirect('exam_detail', exam_id=exam.id)


@login_required
@user_passes_test(is_admin)
def unpublish_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam.is_published = False
    exam.published_at = None
    exam.save()
    messages.warning(request, f"Results for '{exam.name}' have been unpublished.")
    return redirect('exam_detail', exam_id=exam.id)


# ===========================
# ADMIN: Edit Exam
# ===========================
@login_required
@user_passes_test(is_admin)
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        exam.name = request.POST.get('name', '').strip()
        exam.exam_type = request.POST.get('exam_type', 'MID')
        exam.semester = int(request.POST.get('semester', exam.semester))
        exam.start_date = request.POST.get('start_date')
        exam.end_date = request.POST.get('end_date')
        exam.save()

        # Sync subjects
        submitted_ids = set(map(int, request.POST.getlist('subjects')))
        existing_es = {es.subject_id: es for es in exam.exam_subjects.all()}

        # Remove unchecked
        for sid, es in existing_es.items():
            if sid not in submitted_ids:
                es.delete()

        # Add/update
        for sid in submitted_ids:
            marks = request.POST.get(f'marks_{sid}', '20')
            marks_val = int(marks) if marks else 20
            if sid in existing_es:
                es = existing_es[sid]
                if es.total_marks != marks_val:
                    es.total_marks = marks_val
                    es.save()
            else:
                try:
                    subject = Subject.objects.get(id=sid)
                    ExamSubject.objects.create(exam=exam, subject=subject, total_marks=marks_val)
                except Subject.DoesNotExist:
                    pass

        messages.success(request, f"Exam '{exam.name}' updated!")
        return redirect('exam_detail', exam_id=exam.id)

    # GET: load subjects + existing selections
    subjects_by_semester = {}
    for sem in range(1, 7):
        subjects_by_semester[sem] = list(
            Subject.objects.filter(semester=sem).order_by('code').values('id', 'name', 'code')
        )

    # Existing exam subjects with marks
    existing_subjects = {}
    for es in exam.exam_subjects.all():
        existing_subjects[es.subject_id] = es.total_marks

    return render(request, 'exams/edit_exam.html', {
        'exam': exam,
        'subjects_by_semester': json.dumps(subjects_by_semester),
        'existing_subjects': json.dumps(existing_subjects),
    })


# ===========================
# ADMIN: Exam Timetable
# ===========================
@login_required
@user_passes_test(is_admin)
def exam_timetable(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam_subjects = exam.exam_subjects.select_related('subject').all()

    if request.method == "POST":
        saved = 0
        for es in exam_subjects:
            date_val = request.POST.get(f'date_{es.id}', '').strip()
            start_val = request.POST.get(f'start_{es.id}', '').strip()
            end_val = request.POST.get(f'end_{es.id}', '').strip()
            room_val = request.POST.get(f'room_{es.id}', '').strip()

            if date_val and start_val and end_val:
                from datetime import date as dt_date
                parsed_date = dt_date.fromisoformat(date_val)
                if parsed_date < exam.start_date or parsed_date > exam.end_date:
                    continue  # skip dates outside exam range
                ExamSchedule.objects.update_or_create(
                    exam_subject=es,
                    defaults={
                        'exam_date': date_val,
                        'start_time': start_val,
                        'end_time': end_val,
                        'room': room_val,
                    }
                )
                saved += 1

        messages.success(request, f"Timetable saved for {saved} subjects!")
        return redirect('exam_detail', exam_id=exam.id)

    # GET: build data with existing schedules
    subjects_data = []
    for es in exam_subjects:
        try:
            sched = es.schedule
        except ExamSchedule.DoesNotExist:
            sched = None

        subjects_data.append({
            'es': es,
            'schedule': sched,
        })

    return render(request, 'exams/exam_timetable.html', {
        'exam': exam,
        'subjects_data': subjects_data,
    })