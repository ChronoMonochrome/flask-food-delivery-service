#!/bin/bash

# Source the .env file (though not strictly needed for this script if DB_URL is hardcoded)
source .env

# Get the DATABASE_URL from docker-compose.yml (replace with your actual password)
DB_URL="mysql+pymysql://user:your_db_password@db:3306/mydatabase"

echo "!!! DANGER: This script will delete ALL data in your database. !!!"
echo "!!! Are you absolutely sure you want to proceed? (yes/no) !!!"
read -p "Type 'yes' to confirm: " CONFIRMATION

if [[ "$CONFIRMATION" == "yes" ]]; then
  echo "--- Dropping All Database Tables ---"
  docker compose run --rm \
    -e DATABASE_URL="${DB_URL}" \
    scheduler \
    python /app/drop_db_tables.py
  echo "--- Database Tables Dropped ---"
else
  echo "Operation cancelled. No tables were dropped."
fi
