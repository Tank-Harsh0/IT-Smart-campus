from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_welcome_email(user, temp_password):
    try:
        context = {
            'first_name': user.first_name or user.username,
            'username': user.username,
            'temp_password': temp_password,
            'login_url': f"{settings.SITE_URL}/accounts/login/",
            'site_name': 'RCTI IT Smart Campus',
        }
        
        html_content = render_to_string('emails/welcome_user.html', context)
        
        text_content = f"""
Welcome to RCTI Smart Campus, {context['first_name']}!

Your account has been created. Here are your login credentials:

Username: {user.username}
Temporary Password: {temp_password}

Please login at: {context['login_url']}

Important: You will be required to change your password on first login.

Best regards,
RCTI IT Department
"""
        
        subject = '🎓 Welcome to RCTI Smart Campus - Your Login Credentials'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        
        email.send(fail_silently=False)
        
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")
        return False
