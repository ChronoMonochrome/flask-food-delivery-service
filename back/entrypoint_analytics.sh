#!/bin/sh
# entrypoint_analytics.sh

echo "Initializing Analytics SQLite Database..."
python -c "import os; os.makedirs('/app/data', exist_ok=True); from analytics_service import app, db; ctx = app.app_context(); ctx.push(); db.create_all(); ctx.pop()"

echo "Starting Gunicorn for Analytics Service on port 5002..."
exec gunicorn -w 2 -b 0.0.0.0:5002 --access-logfile - --error-logfile - analytics_service:app
