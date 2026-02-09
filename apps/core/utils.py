"""
Email Utility Functions for RCTI Smart Campus
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_welcome_email(user, temp_password):
    """
    Send a welcome email with login credentials to a newly created user.
    
    Args:
        user: The User object (must have email, username, first_name)
        temp_password: The temporary password to include in the email
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Build context for the email template
        context = {
            'first_name': user.first_name or user.username,
            'username': user.username,
            'temp_password': temp_password,
            'login_url': f"{settings.SITE_URL}/accounts/login/",
            'site_name': 'RCTI Smart Campus',
        }
        
        # Render the HTML email template
        html_content = render_to_string('emails/welcome_user.html', context)
        
        # Plain text fallback
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
        
        # Create the email
        subject = '🎓 Welcome to RCTI Smart Campus - Your Login Credentials'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        # Attach HTML version
        email.attach_alternative(html_content, "text/html")
        
        # Send the email
        email.send(fail_silently=False)
        
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")
        return False
