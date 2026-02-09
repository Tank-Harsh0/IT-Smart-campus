import csv
import random
import string
import logging
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import User
from apps.students.models import Student
from apps.faculty.models import Faculty

logger = logging.getLogger(__name__)


def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits + '!@#$%'
    return ''.join(random.choice(chars) for _ in range(length))


def send_credentials_email(user, temp_password, role_type):
    """
    Send login credentials to a newly created user.
    Returns True if email sent successfully, False otherwise.
    """
    try:
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        login_url = f"{site_url}/accounts/login/"
        
        subject = "Your RCTI IT Department Login Credentials"
        
        # Plain text message
        message = f"""
Hello {user.first_name},

Welcome to the RCTI IT Department Portal!

Your login credentials are:
━━━━━━━━━━━━━━━━━━━━━━━
Username: {user.username}
Email: {user.email}
Temporary Password: {temp_password}
Role: {role_type.upper()}
━━━━━━━━━━━━━━━━━━━━━━━

Login URL: {login_url}

⚠️ IMPORTANT: You will be required to change your password on first login.

If you did not request this account, please contact the IT Department immediately.

Best regards,
RCTI IT Department
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Credentials email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send credentials email to {user.email}: {e}")
        return False


class BulkUserUploader:
    """
    Handles parsing and atomic creation of users from CSV text.
    """

    @staticmethod
    def process_csv(lines, role_type):
        """
        lines: list[str] (already decoded text)
        role_type: User.Role.STUDENT or User.Role.FACULTY
        """

        reader = csv.DictReader(lines)

        results = {
            'created': [],
            'errors': []
        }

        for row in reader:
            try:
                with transaction.atomic():

                    email = row.get('email', '').strip()
                    name = row.get('name', '').strip()

                    if not email or not name:
                        raise ValueError("Name or email missing")

                    if User.objects.filter(email=email).exists():
                        raise ValueError(f"Email already exists: {email}")

                    temp_password = generate_random_password()
                    username = email.split('@')[0]

                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=temp_password,
                        role=role_type,
                        first_name=name,
                        must_change_password=True
                    )

                    # -------------------------
                    # STUDENT
                    # -------------------------
                    if role_type == User.Role.STUDENT:
                        enrollment = row.get('enrollment_id', '').strip()
                        semester = int(row.get('semester', 1))

                        if not enrollment:
                            raise ValueError("Enrollment ID missing")

                        Student.objects.create(
                            user=user,
                            enrollment_number=enrollment,
                            semester=semester
                        )

                    # -------------------------
                    # FACULTY
                    # -------------------------
                    elif role_type == User.Role.FACULTY:
                        employee_id = row.get('employee_id', '').strip()
                        designation = row.get('designation', 'Assistant Professor')

                        if not employee_id:
                            raise ValueError("Employee ID missing")

                        Faculty.objects.create(
                            user=user,
                            employee_id=employee_id,
                            designation=designation
                        )

                    # Send credentials email to the new user
                    email_sent = send_credentials_email(user, temp_password, role_type)

                    results['created'].append({
                        'email': email,
                        'temp_password': temp_password,
                        'email_sent': email_sent
                    })

            except Exception as e:
                results['errors'].append({
                    'row': row,
                    'error': str(e)
                })

        return results
