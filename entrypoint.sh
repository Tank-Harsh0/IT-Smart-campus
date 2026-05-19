#!/bin/bash
set -e

if [ "$DB_HOST" != "localhost" ] && [ -n "$DB_HOST" ]; then
    echo "Waiting for MySQL database at $DB_HOST:$DB_PORT..."
    
    # We can use python to try to connect to the database to ensure it's fully ready
    python << END
import sys
import time
import MySQLdb

# Get connection details from environment or use defaults
db_name = "$DB_NAME"
db_user = "$DB_USER"
db_password = "$DB_PASSWORD"
db_host = "$DB_HOST"
db_port = int("${DB_PORT:-3306}")

max_tries = 30
for i in range(max_tries):
    try:
        conn = MySQLdb.connect(
            host=db_host,
            user=db_user,
            passwd=db_password,
            db=db_name,
            port=db_port
        )
        conn.close()
        print("Successfully connected to the database.")
        sys.exit(0)
    except Exception as e:
        print(f"Database not ready yet (Attempt {i+1}/{max_tries}). Waiting 2 seconds...")
        time.sleep(2)

print("Could not connect to the database. Exiting...")
sys.exit(1)
END
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
# If arguments are passed to the container (e.g. from docker-compose `command`), run those
if [ $# -gt 0 ]; then
    exec "$@"
else
    # Default fallback: run using gunicorn
    echo "Starting Gunicorn server..."
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
