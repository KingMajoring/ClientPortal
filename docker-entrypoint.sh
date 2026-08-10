#!/bin/sh
set -e

flask db upgrade

exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 wsgi:app
