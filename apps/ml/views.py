from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q, F, FloatField, ExpressionWrapper
from apps.accounts.decorators import admin_required, faculty_required
from apps.students.models import Student
from apps.attendance.models import AttendanceRecord
from apps.exams.models import ExamResult
from . import predictor

@login_required
@admin_required
def admin_ml_dashboard(request):
    students = list(Student.objects.select_related('user', 'batch'))
    student_ids = [s.id for s in students]
    if not student_ids:
        return render(request, 'ml/admin_ml_dashboard.html', {
            'students': [],
            'high_risk': 0,
            'medium_risk': 0,
            'anomalies': 0,
            'total_students': 0,
        })

    attendance_stats = {
        row['student_id']: row
        for row in (
            AttendanceRecord.objects.filter(student_id__in=student_ids)
            .values('student_id')
            .annotate(
                total_records=Count('id'),
                present_records=Count('id', filter=Q(is_present=True)),
            )
        )
    }
    marks_stats = {
        row['student_id']: row
        for row in (
            ExamResult.objects.filter(student_id__in=student_ids, marks_obtained__isnull=False)
            .values('student_id')
            .annotate(
                avg_marks=Avg(
                    ExpressionWrapper(
                        F('marks_obtained') * 100.0 / F('total_marks'),
                        output_field=FloatField(),
                    ),
                    filter=Q(total_marks__gt=0),
                ),
                failures=Count('id', filter=Q(marks_obtained__lt=10)),
            )
        )
    }
    streak_map = _calculate_max_absent_streaks(student_ids)

    student_insights = []
    for student in students:
        att = attendance_stats.get(student.id, {})
        total_records = att.get('total_records', 0)
        present_records = att.get('present_records', 0)
        attendance_pct = (present_records / total_records * 100) if total_records > 0 else 75.0

        marks = marks_stats.get(student.id, {})
        avg_marks = marks.get('avg_marks') if marks.get('avg_marks') is not None else 50.0
        failures = marks.get('failures', 0)

        risk = predictor.predict_at_risk(
            attendance_pct=attendance_pct,
            avg_marks_pct=avg_marks,
            failures=failures,
        )

        absent_streak = streak_map.get(student.id, 0)
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

    student_insights.sort(key=lambda x: x['risk']['risk_probability'], reverse=True)

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



@login_required
@faculty_required
def faculty_anomaly_alerts(request):
    faculty = request.user.faculty_profile

    from apps.core.models import TimetableSlot
    batch_ids = set(TimetableSlot.objects.filter(faculty=faculty).values_list('batch_id', flat=True))

    students = list(Student.objects.filter(batch_id__in=batch_ids).select_related('user', 'batch'))
    student_ids = [s.id for s in students]
    if not student_ids:
        return render(request, 'ml/faculty_anomaly_alerts.html', {
            'alerts': [],
            'total_alerts': 0,
        })

    attendance_stats = {
        row['student_id']: row
        for row in (
            AttendanceRecord.objects.filter(student_id__in=student_ids)
            .values('student_id')
            .annotate(
                total_records=Count('id'),
                present_records=Count('id', filter=Q(is_present=True)),
            )
        )
    }
    marks_stats = {
        row['student_id']: row
        for row in (
            ExamResult.objects.filter(student_id__in=student_ids, marks_obtained__isnull=False)
            .values('student_id')
            .annotate(
                avg_marks=Avg(
                    ExpressionWrapper(
                        F('marks_obtained') * 100.0 / F('total_marks'),
                        output_field=FloatField(),
                    ),
                    filter=Q(total_marks__gt=0),
                ),
                failures=Count('id', filter=Q(marks_obtained__lt=10)),
            )
        )
    }
    streak_map = _calculate_max_absent_streaks(student_ids)

    student_alerts = []
    for student in students:
        att = attendance_stats.get(student.id, {})
        total_records = att.get('total_records', 0)
        present_records = att.get('present_records', 0)
        attendance_pct = (present_records / total_records * 100) if total_records > 0 else 75.0

        absent_streak = streak_map.get(student.id, 0)
        classes_missed = total_records - present_records

        anomaly = predictor.detect_anomaly(
            attendance_pct=attendance_pct,
            max_absent_streak=absent_streak,
            total_classes_missed=classes_missed,
        )

        marks = marks_stats.get(student.id, {})
        avg_marks = marks.get('avg_marks') if marks.get('avg_marks') is not None else 50.0
        failures = marks.get('failures', 0)

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


def _calculate_max_absent_streaks(student_ids):
    """Calculate max consecutive absent streak for each student in one pass."""
    streak_map = {sid: 0 for sid in student_ids}
    current_map = {sid: 0 for sid in student_ids}

    records = (
        AttendanceRecord.objects
        .filter(student_id__in=student_ids)
        .order_by('student_id', 'session__date')
        .values_list('student_id', 'is_present')
    )

    for student_id, is_present in records:
        if not is_present:
            current_map[student_id] += 1
            if current_map[student_id] > streak_map[student_id]:
                streak_map[student_id] = current_map[student_id]
        else:
            current_map[student_id] = 0

    return streak_map
