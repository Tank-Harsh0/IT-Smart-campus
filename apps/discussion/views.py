from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.decorators import faculty_required
from apps.subjects.models import Subject
from .models import Discussion, Reply


# ===========================
# Discussion List (All roles)
# ===========================
@login_required
def discussion_list(request):
    subject_id = request.GET.get('subject')
    discussions = Discussion.objects.select_related('subject', 'author').all()

    if subject_id:
        discussions = discussions.filter(subject_id=subject_id)

    # Get subjects for the filter dropdown
    subjects = Subject.objects.all()

    return render(request, 'discussion/discussion_list.html', {
        'discussions': discussions,
        'subjects': subjects,
        'selected_subject': int(subject_id) if subject_id else None,
    })


# ===========================
# Create Thread (Student/Faculty)
# ===========================
@login_required
def discussion_create(request):
    subjects = Subject.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        subject_id = request.POST.get('subject')

        if not title or not body or not subject_id:
            messages.error(request, "All fields are required.")
            return redirect('discussion_create')

        subject = get_object_or_404(Subject, id=subject_id)

        # Auto-tag using ML model
        tag = 'Question'  # default
        try:
            from apps.ml.predictor import classify_text
            result = classify_text(title, body)
            tag = result.get('tag', 'Question')
        except Exception:
            pass

        Discussion.objects.create(
            title=title,
            body=body,
            subject=subject,
            author=request.user,
            tag=tag,
        )
        messages.success(request, "Discussion created!")
        return redirect('discussion_list')

    return render(request, 'discussion/discussion_create.html', {'subjects': subjects})


# ===========================
# Discussion Detail + Replies
# ===========================
@login_required
def discussion_detail(request, discussion_id):
    discussion = get_object_or_404(
        Discussion.objects.select_related('subject', 'author'),
        id=discussion_id
    )
    replies = discussion.replies.select_related('author').all()

    # POST: Add a reply
    if request.method == 'POST' and not discussion.is_closed:
        body = request.POST.get('body', '').strip()
        if body:
            Reply.objects.create(
                discussion=discussion,
                author=request.user,
                body=body,
            )
            messages.success(request, "Reply posted!")
        return redirect('discussion_detail', discussion_id=discussion.id)

    return render(request, 'discussion/discussion_detail.html', {
        'discussion': discussion,
        'replies': replies,
    })


# ===========================
# Pin / Unpin (Faculty only)
# ===========================
@login_required
@faculty_required
def discussion_pin(request, discussion_id):
    discussion = get_object_or_404(Discussion, id=discussion_id)
    discussion.is_pinned = not discussion.is_pinned
    discussion.save()
    action = "pinned" if discussion.is_pinned else "unpinned"
    messages.success(request, f"Discussion {action}.")
    return redirect('discussion_detail', discussion_id=discussion.id)


# ===========================
# Close / Reopen (Faculty only)
# ===========================
@login_required
@faculty_required
def discussion_close(request, discussion_id):
    discussion = get_object_or_404(Discussion, id=discussion_id)
    discussion.is_closed = not discussion.is_closed
    discussion.save()
    action = "closed" if discussion.is_closed else "reopened"
    messages.success(request, f"Discussion {action}.")
    return redirect('discussion_detail', discussion_id=discussion.id)
