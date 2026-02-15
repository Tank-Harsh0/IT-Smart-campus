import json
import logging
import face_recognition
import numpy as np
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.accounts.decorators import faculty_required
from apps.subjects.models import Subject
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
    return render(request, 'attendance/take_attendance.html', {'session': session})

@login_required
@faculty_required
def recognize_face(request, session_id):
    if request.method == 'POST':
        try:
            session = get_object_or_404(AttendanceSession, id=session_id)
            
            # 1. Get Image from Webcam (sent as form data)
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'status': 'error', 'message': 'No image data'})

            # 2. Load & Encode the "Unknown" Image
            unknown_image = face_recognition.load_image_file(image_file)
            unknown_encodings = face_recognition.face_encodings(unknown_image)

            if not unknown_encodings:
                return JsonResponse({'status': 'failed', 'message': 'No face detected'})

            # 3. Load "Known" Faces from DB
            # (Optimization: In a real giant app, you'd cache this in Redis)
            known_faces_qs = FaceData.objects.exclude(encoding_json__isnull=True)
            known_encodings = []
            known_students = []

            for fd in known_faces_qs:
                try:
                    # Convert stored JSON list back to Numpy Array
                    encoding = fd.get_encoding()
                    known_encodings.append(encoding)
                    known_students.append(fd.student)
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(f"Bad face encoding for student {fd.student}: {e}")
                    continue

            identified_names = []

            # 4. Compare Faces
            for unknown_encoding in unknown_encodings:
                # Tolerance: Lower is stricter (0.6 is default, 0.5 is safer)
                matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.5)
                
                if True in matches:
                    first_match_index = matches.index(True)
                    student = known_students[first_match_index]
                    
                    # 5. Mark Attendance (Prevent duplicates for this session)
                    record, created = AttendanceRecord.objects.get_or_create(
                        session=session,
                        student=student,
                        defaults={
                            'is_present': True,
                            'method': 'FACE'
                        }
                    )
                    
                    if created:
                        identified_names.append(f"{student.user.first_name} (Marked Present)")
                    else:
                        identified_names.append(f"{student.user.first_name} (Already Marked)")

            return JsonResponse({'status': 'success', 'identified': identified_names})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})