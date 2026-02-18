from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import admin_required, faculty_required
from apps.students.models import Student
from apps.attendance.models import AttendanceSession, AttendanceRecord
from apps.exams.models import ExamResult
from . import predictor


# ===========================
# ADMIN: ML Insights Dashboard
# ===========================
@login_required
@admin_required
def admin_ml_dashboard(request):
    students = Student.objects.select_related('user', 'batch').all()

    student_insights = []
    for student in students:
        # Calculate attendance %
        total_records = AttendanceRecord.objects.filter(student=student).count()
        present_records = AttendanceRecord.objects.filter(student=student, is_present=True).count()
        attendance_pct = (present_records / total_records * 100) if total_records > 0 else 75.0

        # Calculate average marks %
        results = ExamResult.objects.filter(student=student, marks_obtained__isnull=False)
        if results.exists():
            avg_marks = sum(r.percentage for r in results) / results.count()
        else:
            avg_marks = 50.0

        # Count failures
        failures = results.filter(marks_obtained__lt=10).count() if results.exists() else 0

        # Predict at-risk
        risk = predictor.predict_at_risk(
            attendance_pct=attendance_pct,
            avg_marks_pct=avg_marks,
            failures=failures,
        )

        # Detect anomaly
        absent_streak = _calculate_max_absent_streak(student)
        classes_missed = total_records - present_records
        anomaly = predictor.detect_anomaly(
            attendance_pct=attendance_pct,
            max_absent_streak=absent_streak,
            total_classes_missed=classes_missed,
        )

        student_insights.append({
            'student': student,
            'attendance_pct': round(attendance_pct, 1),
            'avg_marks': round(avg_marks, 1),
            'risk': risk,
            'anomaly': anomaly,
        })

    # Sort: high-risk first
    student_insights.sort(key=lambda x: x['risk']['risk_probability'], reverse=True)

    # Stats
    high_risk = sum(1 for s in student_insights if s['risk']['risk_level'] == 'High')
    medium_risk = sum(1 for s in student_insights if s['risk']['risk_level'] == 'Medium')
    anomalies = sum(1 for s in student_insights if s['anomaly']['is_anomaly'])

    return render(request, 'ml/admin_ml_dashboard.html', {
        'students': student_insights,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'anomalies': anomalies,
        'total_students': len(student_insights),
    })


# ===========================
# FACULTY: Anomaly Alerts
# ===========================
@login_required
@faculty_required
def faculty_anomaly_alerts(request):
    faculty = request.user.faculty_profile

    # Get subjects taught by this faculty
    from apps.core.models import TimetableSlot
    faculty_slots = TimetableSlot.objects.filter(faculty=faculty).select_related('batch')
    batch_ids = set(faculty_slots.values_list('batch_id', flat=True))

    # Get students from those batches
    students = Student.objects.filter(batch_id__in=batch_ids).select_related('user', 'batch')

    student_alerts = []
    for student in students:
        total_records = AttendanceRecord.objects.filter(student=student).count()
        present_records = AttendanceRecord.objects.filter(student=student, is_present=True).count()
        attendance_pct = (present_records / total_records * 100) if total_records > 0 else 75.0

        absent_streak = _calculate_max_absent_streak(student)
        classes_missed = total_records - present_records

        anomaly = predictor.detect_anomaly(
            attendance_pct=attendance_pct,
            max_absent_streak=absent_streak,
            total_classes_missed=classes_missed,
        )

        # Also get risk prediction
        results = ExamResult.objects.filter(student=student, marks_obtained__isnull=False)
        avg_marks = (sum(r.percentage for r in results) / results.count()) if results.exists() else 50.0
        failures = results.filter(marks_obtained__lt=10).count() if results.exists() else 0

        risk = predictor.predict_at_risk(
            attendance_pct=attendance_pct,
            avg_marks_pct=avg_marks,
            failures=failures,
        )

        if anomaly['is_anomaly'] or risk['risk_level'] in ('High', 'Medium'):
            student_alerts.append({
                'student': student,
                'attendance_pct': round(attendance_pct, 1),
                'avg_marks': round(avg_marks, 1),
                'absent_streak': absent_streak,
                'anomaly': anomaly,
                'risk': risk,
            })

    student_alerts.sort(key=lambda x: x['risk']['risk_probability'], reverse=True)

    return render(request, 'ml/faculty_anomaly_alerts.html', {
        'alerts': student_alerts,
        'total_alerts': len(student_alerts),
    })


def _calculate_max_absent_streak(student):
    """Calculate the maximum consecutive absent streak for a student."""
    records = (
        AttendanceRecord.objects
        .filter(student=student)
        .order_by('session__date')
        .values_list('is_present', flat=True)
    )
    max_streak = 0
    current_streak = 0
    for is_present in records:
        if not is_present:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    return max_streak
