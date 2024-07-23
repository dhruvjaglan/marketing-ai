#!/bin/bash

# Start gunicorn
gunicorn --bind 127.0.0.1:8000 django_backend.wsgi:application &

# Start celery
celery -A django_backend worker --loglevel=info &

# Wait for both processes to end
wait

