"""
Test email sending functionality.
Usage: python manage.py test_email your_email@example.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Email address to send test email to')
        parser.add_argument('--force-smtp', action='store_true', help='Force SMTP even in DEBUG mode')

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📧 EMAIL CONFIGURATION TEST")
        self.stdout.write("=" * 50)
        
        # Show current config
        self.stdout.write(f"\n🔧 Current Settings:")
        self.stdout.write(f"   DEBUG: {settings.DEBUG}")
        self.stdout.write(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Force SMTP if requested
        if options['force_smtp']:
            self.stdout.write(f"\n⚡ Forcing SMTP backend...")
            from django.core.mail import EmailMessage
            from django.core.mail.backends.smtp import EmailBackend
            
            # Create custom backend
            backend = EmailBackend(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                timeout=settings.EMAIL_TIMEOUT,
            )
            
            email = EmailMessage(
                subject="🧪 RCTI IT Department - Email Test",
                body=f"""
Hello!

This is a test email from the RCTI IT Department Portal.

If you received this, your email configuration is working correctly! ✅

Configuration used:
- Host: {settings.EMAIL_HOST}
- Port: {settings.EMAIL_PORT}
- User: {settings.EMAIL_HOST_USER}

Best regards,
RCTI IT Department System
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            
            try:
                email.send(fail_silently=False)
                self.stdout.write(self.style.SUCCESS(f"\n✅ Email sent successfully to {recipient}!"))
                self.stdout.write("Check your inbox (and spam folder).")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Email failed: {e}"))
                self.stdout.write("\nPossible issues:")
                self.stdout.write("  1. Gmail App Password may be incorrect")
                self.stdout.write("  2. Less secure apps might be blocked")
                self.stdout.write("  3. Network/firewall issues")
        else:
            # Use default backend
            self.stdout.write(f"\n📤 Sending test email to: {recipient}")
            
            try:
                send_mail(
                    subject="🧪 RCTI IT Department - Email Test",
                    message=f"""
Hello!

This is a test email from the RCTI IT Department Portal.

If you received this, your email configuration is working correctly! ✅

Best regards,
RCTI IT Department System
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                
                if 'console' in settings.EMAIL_BACKEND.lower():
                    self.stdout.write(self.style.WARNING(f"\n⚠️ Email printed to CONSOLE (not actually sent)"))
                    self.stdout.write("To send real emails, use: --force-smtp flag")
                else:
                    self.stdout.write(self.style.SUCCESS(f"\n✅ Email sent successfully to {recipient}!"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Email failed: {e}"))
        
        self.stdout.write("\n" + "=" * 50 + "\n")
