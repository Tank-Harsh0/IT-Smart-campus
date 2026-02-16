#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements-deploy.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create superuser automatically (only if it doesn't exist)
echo "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@rcti.edu', 'Admin@123')
    user.role = 'ADMIN'
    user.save()
    print('Superuser created: admin / Admin@123')
else:
    print('Superuser already exists')
" | python manage.py shell
