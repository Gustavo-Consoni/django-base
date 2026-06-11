#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --clear --noinput

exec gunicorn core.wsgi:application \
    --bind unix:/run/gunicorn/gunicorn.sock \
    --workers 2 \
    --threads 4 \
    --timeout 30
