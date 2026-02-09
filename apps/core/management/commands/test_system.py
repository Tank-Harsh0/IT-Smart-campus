"""
Full System Audit Management Command
=====================================
Tests URL patterns, model integrity, and form validation across the entire Django app.

Usage:
    python manage.py test_system
    python manage.py test_system --urls-only
    python manage.py test_system --models-only
    python manage.py test_system --forms-only
"""
import time
from io import StringIO
from django.core.management.base import BaseCommand
from django.test import Client, RequestFactory
from django.urls import get_resolver, URLPattern, URLResolver
from django.contrib.auth import get_user_model
from django.apps import apps
from django.db import connection
from colorama import Fore, Style, init

# Initialize colorama for Windows
init()

User = get_user_model()


class Command(BaseCommand):
    help = 'Full system audit: URLs, Models, Forms'

    def add_arguments(self, parser):
        parser.add_argument('--urls-only', action='store_true', help='Only test URLs')
        parser.add_argument('--models-only', action='store_true', help='Only test Models')
        parser.add_argument('--forms-only', action='store_true', help='Only test Forms')
        parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.client = Client()
        self.results = {'urls': [], 'models': [], 'forms': []}
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"{Fore.CYAN}🔍 DJANGO SYSTEM AUDIT{Style.RESET_ALL}")
        self.stdout.write("=" * 60 + "\n")
        
        run_all = not (options['urls_only'] or options['models_only'] or options['forms_only'])
        
        if run_all or options['urls_only']:
            self.test_urls()
        
        if run_all or options['models_only']:
            self.test_models()
        
        if run_all or options['forms_only']:
            self.test_forms()
        
        self.print_summary()

    def test_urls(self):
        """Test all URL patterns with authenticated and unauthenticated requests"""
        self.stdout.write(f"\n{Fore.YELLOW}━━━ TASK 1: URL PATTERN CHECK ━━━{Style.RESET_ALL}\n")
        
        # Create test users for different roles
        test_users = self._create_test_users()
        
        # Get all URL patterns
        resolver = get_resolver()
        urls = self._get_all_urls(resolver)
        
        self.stdout.write(f"Found {len(urls)} URL patterns to test\n")
        
        results = {'ok': [], 'redirect': [], 'error': [], 'skipped': []}
        
        for url_info in urls:
            url = url_info['path']
            name = url_info.get('name', 'unnamed')
            
            # Skip admin and static URLs
            if url.startswith('/admin/') or url.startswith('/static/') or url.startswith('/__'):
                results['skipped'].append((url, 'Skipped (admin/static)'))
                continue
            
            # Skip URLs with parameters that can't be auto-filled
            if '<' in url and '>' in url:
                # Try to fill common parameter patterns
                test_url = self._fill_url_params(url)
                if test_url is None:
                    results['skipped'].append((url, 'Skipped (requires params)'))
                    continue
                url = test_url
            
            # Test as anonymous user first
            status, role = self._test_url(url, None)
            
            if status in [401, 403, 302]:
                # Try with authenticated users
                for role_name, user in test_users.items():
                    if user:
                        status, role = self._test_url(url, user)
                        if status == 200:
                            break
            
            # Categorize result
            if status == 200:
                results['ok'].append((url, f"✅ 200 OK ({role})"))
                symbol = f"{Fore.GREEN}✅{Style.RESET_ALL}"
            elif status in [301, 302]:
                results['redirect'].append((url, f"↪️ {status} Redirect ({role})"))
                symbol = f"{Fore.YELLOW}↪️{Style.RESET_ALL}"
            else:
                results['error'].append((url, f"❌ {status} ({role})"))
                symbol = f"{Fore.RED}❌{Style.RESET_ALL}"
            
            if self.verbose:
                self.stdout.write(f"  {symbol} [{status}] {url} ({role})")
        
        self.results['urls'] = results
        
        # Print summary
        self.stdout.write(f"\n{Fore.GREEN}✅ OK (200): {len(results['ok'])}{Style.RESET_ALL}")
        self.stdout.write(f"{Fore.YELLOW}↪️ Redirects: {len(results['redirect'])}{Style.RESET_ALL}")
        self.stdout.write(f"{Fore.RED}❌ Errors: {len(results['error'])}{Style.RESET_ALL}")
        self.stdout.write(f"⏭️ Skipped: {len(results['skipped'])}")
        
        if results['error']:
            self.stdout.write(f"\n{Fore.RED}Problem URLs:{Style.RESET_ALL}")
            for url, msg in results['error']:
                self.stdout.write(f"  • {url} - {msg}")

    def _create_test_users(self):
        """Create or get test users for each role"""
        users = {}
        
        # Superuser
        try:
            users['superuser'] = User.objects.filter(is_superuser=True).first()
            if not users['superuser']:
                users['superuser'] = User.objects.create_superuser(
                    username='test_admin',
                    email='test_admin@test.com',
                    password='testpass123'
                )
        except Exception as e:
            users['superuser'] = None
            self.stdout.write(f"  ⚠️ Could not create superuser: {e}")
        
        # Student
        try:
            from apps.students.models import Student
            student = Student.objects.select_related('user').first()
            users['student'] = student.user if student else None
        except Exception:
            users['student'] = None
        
        # Faculty  
        try:
            from apps.faculty.models import Faculty
            faculty = Faculty.objects.select_related('user').first()
            users['faculty'] = faculty.user if faculty else None
        except Exception:
            users['faculty'] = None
        
        return users

    def _get_all_urls(self, resolver, prefix=''):
        """Recursively get all URL patterns"""
        urls = []
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                new_prefix = prefix + str(pattern.pattern)
                urls.extend(self._get_all_urls(pattern, new_prefix))
            elif isinstance(pattern, URLPattern):
                url_path = prefix + str(pattern.pattern)
                # Convert regex/path to actual URL
                url_path = '/' + url_path.replace('^', '').replace('$', '')
                urls.append({
                    'path': url_path,
                    'name': pattern.name,
                    'callback': pattern.callback
                })
        return urls

    def _fill_url_params(self, url):
        """Try to fill URL parameters with test values"""
        import re
        
        param_map = {
            '<int:pk>': '1',
            '<int:id>': '1',
            '<int:student_id>': '1',
            '<int:faculty_id>': '1',
            '<int:subject_id>': '1',
            '<slug:slug>': 'test-slug',
            '<str:username>': 'admin',
            '<uuid:uuid>': '12345678-1234-5678-1234-567812345678',
        }
        
        result = url
        for param, value in param_map.items():
            result = result.replace(param, value)
        
        # If still has unfilled params, return None
        if '<' in result and '>' in result:
            return None
        
        return result

    def _test_url(self, url, user=None):
        """Test a single URL and return status code"""
        try:
            if user:
                self.client.force_login(user)
                role = getattr(user, 'role', 'authenticated')
            else:
                self.client.logout()
                role = 'anonymous'
            
            response = self.client.get(url, follow=False)
            return response.status_code, role
        except Exception as e:
            return 500, f'error: {str(e)[:30]}'

    def test_models(self):
        """Test all models for integrity"""
        self.stdout.write(f"\n{Fore.YELLOW}━━━ TASK 2: MODEL VALIDATION ━━━{Style.RESET_ALL}\n")
        
        results = {'ok': [], 'error': []}
        
        # Get all models from our apps
        our_apps = ['accounts', 'core', 'students', 'faculty', 'subjects', 'attendance', 'notifications', 'timetable', 'exams']
        
        for app_label in our_apps:
            try:
                app_models = apps.get_app_config(app_label).get_models()
            except LookupError:
                continue
            
            for model in app_models:
                model_name = f"{app_label}.{model.__name__}"
                try:
                    # Test queryset
                    queryset = model.objects.all()[:5]
                    count = queryset.count()
                    
                    # Test __str__ method
                    str_works = True
                    for obj in queryset:
                        try:
                            str(obj)
                        except Exception as e:
                            str_works = False
                            results['error'].append((model_name, f"__str__ error: {e}"))
                            break
                    
                    if str_works:
                        results['ok'].append((model_name, f"✅ OK ({count} records tested)"))
                        if self.verbose:
                            self.stdout.write(f"  {Fore.GREEN}✅{Style.RESET_ALL} {model_name} ({count} records)")
                
                except Exception as e:
                    results['error'].append((model_name, f"Query error: {e}"))
                    if self.verbose:
                        self.stdout.write(f"  {Fore.RED}❌{Style.RESET_ALL} {model_name}: {e}")
        
        self.results['models'] = results
        
        self.stdout.write(f"\n{Fore.GREEN}✅ Models OK: {len(results['ok'])}{Style.RESET_ALL}")
        self.stdout.write(f"{Fore.RED}❌ Models with Errors: {len(results['error'])}{Style.RESET_ALL}")
        
        if results['error']:
            self.stdout.write(f"\n{Fore.RED}Problem Models:{Style.RESET_ALL}")
            for model, msg in results['error']:
                self.stdout.write(f"  • {model} - {msg}")

    def test_forms(self):
        """Test key forms with mock data"""
        self.stdout.write(f"\n{Fore.YELLOW}━━━ TASK 3: FORM VALIDATION ━━━{Style.RESET_ALL}\n")
        
        results = {'ok': [], 'error': []}
        
        # Define forms to test with mock data
        forms_to_test = [
            {
                'name': 'LoginForm (accounts)',
                'import': 'apps.accounts.forms.LoginForm',
                'data': {'username': 'testuser', 'password': 'testpass123'}
            },
            {
                'name': 'ManualTimetableForm (timetable)',
                'import': 'apps.timetable.forms.ManualTimetableForm',
                'data': {'day': 'MON', 'start_time': '09:00', 'end_time': '10:00'}
            },
            {
                'name': 'StudentForm (students)',
                'import': 'apps.students.forms.StudentForm',
                'data': {'enrollment_no': 'TEST001', 'semester': 1}
            },
        ]
        
        for form_info in forms_to_test:
            name = form_info['name']
            try:
                # Dynamic import
                module_path, class_name = form_info['import'].rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                FormClass = getattr(module, class_name)
                
                # Instantiate with mock data
                form = FormClass(data=form_info['data'])
                is_valid = form.is_valid()
                
                if is_valid:
                    results['ok'].append((name, "✅ Valid with test data"))
                    self.stdout.write(f"  {Fore.GREEN}✅{Style.RESET_ALL} {name}: form.is_valid() = True")
                else:
                    errors = dict(form.errors)
                    results['error'].append((name, f"Invalid: {errors}"))
                    self.stdout.write(f"  {Fore.YELLOW}⚠️{Style.RESET_ALL} {name}: form.is_valid() = False")
                    if self.verbose:
                        self.stdout.write(f"      Errors: {errors}")
                        
            except ImportError as e:
                results['error'].append((name, f"Import error: {e}"))
                self.stdout.write(f"  {Fore.RED}❌{Style.RESET_ALL} {name}: Import failed - {e}")
            except Exception as e:
                results['error'].append((name, f"Error: {e}"))
                self.stdout.write(f"  {Fore.RED}❌{Style.RESET_ALL} {name}: {e}")
        
        self.results['forms'] = results

    def print_summary(self):
        """Print final summary"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"{Fore.CYAN}📊 AUDIT SUMMARY{Style.RESET_ALL}")
        self.stdout.write("=" * 60)
        
        total_ok = 0
        total_errors = 0
        
        if 'urls' in self.results and self.results['urls']:
            url_ok = len(self.results['urls'].get('ok', []))
            url_err = len(self.results['urls'].get('error', []))
            total_ok += url_ok
            total_errors += url_err
            self.stdout.write(f"\n📍 URLs: {url_ok} OK, {url_err} errors")
        
        if 'models' in self.results and self.results['models']:
            model_ok = len(self.results['models'].get('ok', []))
            model_err = len(self.results['models'].get('error', []))
            total_ok += model_ok
            total_errors += model_err
            self.stdout.write(f"🗄️ Models: {model_ok} OK, {model_err} errors")
        
        if 'forms' in self.results and self.results['forms']:
            form_ok = len(self.results['forms'].get('ok', []))
            form_err = len(self.results['forms'].get('error', []))
            total_ok += form_ok
            total_errors += form_err
            self.stdout.write(f"📝 Forms: {form_ok} OK, {form_err} errors")
        
        self.stdout.write("\n" + "-" * 60)
        
        if total_errors == 0:
            self.stdout.write(f"{Fore.GREEN}🎉 ALL TESTS PASSED! System is healthy.{Style.RESET_ALL}")
        else:
            self.stdout.write(f"{Fore.RED}⚠️ {total_errors} issues found. Please review above.{Style.RESET_ALL}")
        
        self.stdout.write("=" * 60 + "\n")
