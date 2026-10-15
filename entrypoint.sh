#!/bin/sh
# Zamzam Foods — Production Entrypoint
# Runs migrations, creates superuser if needed, then starts Gunicorn

set -e

echo ">>> Running database migrations..."
python manage.py migrate --noinput || echo ">>> WARNING: Database migrations failed or timed out, continuing server startup..."

echo ">>> Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@zamzam.com'),
        password=os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123!')
    )
    print(f'Superuser \"{username}\" created.')
else:
    print(f'Superuser \"{username}\" already exists, skipping.')
" || echo ">>> WARNING: Superuser verification skipped."

echo ">>> Starting Gunicorn on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
