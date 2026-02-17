from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.accounts.decorators import faculty_required, admin_required, student_required
from apps.faculty.models import Faculty
from apps.core.models import TimetableSlot
from .models import FacultyLeave


# ===========================
# FACULTY: Apply for Leave
# ===========================
@login_required
@faculty_required
def faculty_leave_apply(request):
    faculty = request.user.faculty_profile

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason', '').strip()

        if not start_date or not end_date or not reason:
            messages.error(request, "All fields are required.")
            return redirect('faculty_leave_apply')

        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        if end < start:
            messages.error(request, "End date cannot be before start date.")
            return redirect('faculty_leave_apply')

        if start < timezone.now().date():
            messages.error(request, "Cannot apply for leave in the past.")
            return redirect('faculty_leave_apply')

        FacultyLeave.objects.create(
            faculty=faculty,
            start_date=start,
            end_date=end,
            reason=reason,
        )
        messages.success(request, "Leave request submitted successfully!")
        return redirect('faculty_leave_history')

    return render(request, 'leave/faculty_leave_apply.html')


# ===========================
# FACULTY: Leave History
# ===========================
@login_required
@faculty_required
def faculty_leave_history(request):
    faculty = request.user.faculty_profile
    leaves = FacultyLeave.objects.filter(faculty=faculty)
    return render(request, 'leave/faculty_leave_history.html', {'leaves': leaves})


# ===========================
# ADMIN: All Leave Requests
# ===========================
@login_required
@admin_required
def admin_leave_requests(request):
    status_filter = request.GET.get('status', '')
    leaves = FacultyLeave.objects.select_related('faculty__user', 'reviewed_by').all()

    if status_filter:
        leaves = leaves.filter(status=status_filter)

    pending_count = FacultyLeave.objects.filter(status='PENDING').count()

    return render(request, 'leave/admin_leave_requests.html', {
        'leaves': leaves,
        'status_filter': status_filter,
        'pending_count': pending_count,
    })


# ===========================
# ADMIN: Approve / Reject
# ===========================
@login_required
@admin_required
def admin_leave_action(request, leave_id):
    leave = get_object_or_404(FacultyLeave, id=leave_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '').strip()

        if action == 'approve':
            leave.status = 'APPROVED'
            messages.success(request, f"Leave for {leave.faculty} approved.")
        elif action == 'reject':
            leave.status = 'REJECTED'
            messages.warning(request, f"Leave for {leave.faculty} rejected.")
        else:
            messages.error(request, "Invalid action.")
            return redirect('admin_leave_requests')

        leave.reviewed_by = request.user
        leave.review_remarks = remarks
        leave.reviewed_at = timezone.now()
        leave.save()

    return redirect('admin_leave_requests')


# ===========================
# STUDENT: Absent Faculty Today
# ===========================
@login_required
@student_required
def student_faculty_absent(request):
    today = timezone.now().date()

    # Day mapping for timetable lookup
    WEEKDAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
    current_day = WEEKDAY_MAP.get(today.weekday())

    # Find all approved leaves covering today
    approved_leaves = FacultyLeave.objects.filter(
        status='APPROVED',
        start_date__lte=today,
        end_date__gte=today,
    ).select_related('faculty__user')

    absent_faculty_ids = approved_leaves.values_list('faculty_id', flat=True)

    # Get student's semester to find relevant timetable slots
    student = request.user.student_profile
    semester_slots = TimetableSlot.objects.filter(
        batch__classroom__semester=student.semester,
        day=current_day,
    ).select_related('faculty__user', 'subject', 'batch')

    # Separate into affected (cancelled) and unaffected slots
    cancelled_slots = semester_slots.filter(faculty_id__in=absent_faculty_ids)
    active_slots = semester_slots.exclude(faculty_id__in=absent_faculty_ids)

    # Build absent faculty info with their leaves
    absent_faculty_info = []
    for leave in approved_leaves:
        faculty_slots = cancelled_slots.filter(faculty=leave.faculty)
        absent_faculty_info.append({
            'faculty': leave.faculty,
            'leave': leave,
            'affected_slots': faculty_slots,
        })

    return render(request, 'leave/student_absent_faculty.html', {
        'today': today,
        'current_day': current_day,
        'absent_faculty_info': absent_faculty_info,
        'cancelled_slots': cancelled_slots,
        'active_slots': active_slots,
        'has_absent': len(absent_faculty_info) > 0,
    })
