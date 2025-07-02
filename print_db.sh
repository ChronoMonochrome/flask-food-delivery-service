#!/bin/bash

# Source the .env file to get environment variables like IIKO_API_URL, IIKO_API_TOKEN
# Note: DATABASE_URL is typically defined in docker-compose.yml for services.
# We'll pass it explicitly in the docker compose run command.
source .env

# Get the DATABASE_URL from docker-compose.yml (replace with your actual password)
# It's safer to read it from the docker-compose.yml directly or ensure your host's DATABASE_URL is set.
# For this example, I'll hardcode it as per your docker-compose.yml structure.
DB_URL="mysql+pymysql://user:your_db_password@db:3306/mydatabase"

echo "--- Printing Database Data ---"
docker compose run --rm \
  -e DATABASE_URL="${DB_URL}" \
  -e IIKO_API_URL="${IIKO_API_URL}" \
  -e IIKO_API_TOKEN="${IIKO_API_TOKEN}" \
  scheduler \
  python /app/print_db_data.py

echo "--- Database Data Print Complete ---"
