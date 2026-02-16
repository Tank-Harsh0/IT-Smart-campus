import json
import logging
import face_recognition
import numpy as np
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from apps.accounts.decorators import faculty_required
from apps.subjects.models import Subject
from apps.students.models import Student
from apps.core.models import TimetableSlot
from apps.attendance.models import FaceData, AttendanceSession, AttendanceRecord

logger = logging.getLogger(__name__)

# Day mapping: Python weekday (0=Mon) → our model's day code
WEEKDAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
BUFFER_MINUTES = 10  # Allow ±10 min flexibility

@login_required
@faculty_required
def start_session(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    faculty = request.user.faculty_profile

    # --- Time Validation: Only allow during scheduled hours ---
    now = timezone.localtime()
    current_day = WEEKDAY_MAP.get(now.weekday())
    current_time = now.time()

    # Find matching timetable slot for this faculty + subject + current day
    # with ±10 min buffer on start/end times
    buffer = timedelta(minutes=BUFFER_MINUTES)
    buffered_start = (now - buffer).time()
    buffered_end = (now + buffer).time()

    matching_slot = TimetableSlot.objects.filter(
        faculty=faculty,
        subject=subject,
        day=current_day,
        start_time__lte=buffered_end,   # class starts before current time + buffer
        end_time__gte=buffered_start,   # class ends after current time - buffer
    ).first()

    if not matching_slot:
        messages.error(
            request,
            f"❌ No class scheduled for \"{subject.name}\" right now. "
            f"Attendance can only be taken during scheduled hours (±{BUFFER_MINUTES} min)."
        )
        return redirect('faculty_attendance')
    
    # Create a new active session for today
    session = AttendanceSession.objects.create(
        subject=subject,
        status=True
    )

    # Pre-load and cache face encodings for this session's semester
    semester = subject.semester
    cache_key = f"face_enc_{session.id}"

    semester_students = Student.objects.filter(semester=semester).values_list('id', flat=True)
    known_faces_qs = FaceData.objects.filter(
        student_id__in=semester_students
    ).exclude(encoding_json__isnull=True).select_related('student__user')

    cached_data = []
    for fd in known_faces_qs:
        try:
            encoding = fd.get_encoding()
            cached_data.append({
                'encoding': encoding.tolist(),
                'student_id': fd.student_id,
                'name': fd.student.user.first_name,
            })
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Bad face encoding for student {fd.student}: {e}")
            continue

    # Cache for 2 hours (session lifetime)
    cache.set(cache_key, cached_data, timeout=7200)

    return render(request, 'attendance/take_attendance.html', {'session': session})

@login_required
@faculty_required
def recognize_face(request, session_id):
    if request.method == 'POST':
        try:
            session = get_object_or_404(AttendanceSession, id=session_id)
            
            # 1. Get Image from Webcam
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'status': 'error', 'message': 'No image data'})

            # 2. Load & Encode the "Unknown" Image
            unknown_image = face_recognition.load_image_file(image_file)
            unknown_encodings = face_recognition.face_encodings(unknown_image)

            if not unknown_encodings:
                return JsonResponse({'status': 'failed', 'message': 'No face detected'})

            # 3. Load "Known" Faces from CACHE (not DB)
            cache_key = f"face_enc_{session_id}"
            cached_data = cache.get(cache_key)

            if cached_data is None:
                # Fallback: rebuild cache if expired
                semester = session.subject.semester
                semester_students = Student.objects.filter(semester=semester).values_list('id', flat=True)
                known_faces_qs = FaceData.objects.filter(
                    student_id__in=semester_students
                ).exclude(encoding_json__isnull=True).select_related('student__user')

                cached_data = []
                for fd in known_faces_qs:
                    try:
                        encoding = fd.get_encoding()
                        cached_data.append({
                            'encoding': encoding.tolist(),
                            'student_id': fd.student_id,
                            'name': fd.student.user.first_name,
                        })
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        logger.warning(f"Bad face encoding for student {fd.student}: {e}")
                        continue
                cache.set(cache_key, cached_data, timeout=7200)

            known_encodings = [np.array(d['encoding']) for d in cached_data]
            known_student_ids = [d['student_id'] for d in cached_data]
            known_names = [d['name'] for d in cached_data]

            identified_names = []

            # 4. Compare Faces
            for unknown_encoding in unknown_encodings:
                matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.5)
                
                if True in matches:
                    first_match_index = matches.index(True)
                    student_id = known_student_ids[first_match_index]
                    name = known_names[first_match_index]
                    
                    # 5. Mark Attendance (Prevent duplicates)
                    record, created = AttendanceRecord.objects.get_or_create(
                        session=session,
                        student_id=student_id,
                        defaults={
                            'is_present': True,
                            'method': 'FACE'
                        }
                    )
                    
                    if created:
                        identified_names.append(f"{name} (Marked Present)")
                    else:
                        identified_names.append(f"{name} (Already Marked)")

            return JsonResponse({'status': 'success', 'identified': identified_names})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})