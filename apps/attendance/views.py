import json
import logging
import face_recognition
import numpy as np
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from apps.accounts.decorators import faculty_required
from apps.subjects.models import Subject
from apps.students.models import Student
from apps.attendance.models import FaceData, AttendanceSession, AttendanceRecord

logger = logging.getLogger(__name__)

@login_required
@faculty_required
def start_session(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
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