#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

source .env # Keep this for variables used by the script itself (e.g., NETWORK_NAME, PROJECT_DIR)

# --- Configuration Variables (Replace with your actual values) ---

# Docker Hub images base name and tag
export BASE_IMAGE_NAME="flask-mandarin" # This must match how your images are named/tagged
export TAG="latest"                     # This must match how your images are named/tagged

# IMPORTANT: PROJECT_DIR should be the root of your project where 'back/' and 'front/' reside.
# This assumes you run 'start.sh' from the root of your repository.
export PROJECT_DIR=$(pwd)

# --- Build Docker Images Locally ---
echo "Building Docker images locally..."
# Ensure your Dockerfiles are at the root level unless specified otherwise.
# Adjust paths if your Dockerfiles are located differently (e.g., in a 'dockerfiles/' folder).
docker build -f Dockerfile.web -t "${BASE_IMAGE_NAME}-web:${TAG}" . || { echo "Web image build failed!"; exit 1; }
docker build -f Dockerfile.bot -t "${BASE_IMAGE_NAME}-bot:${TAG}" . || { echo "Bot image build failed!"; exit 1; }
docker build -f Dockerfile.scheduler -t "${BASE_IMAGE_NAME}-scheduler:${TAG}" . || { echo "Scheduler image build failed!"; exit 1; }
docker build -f Dockerfile.nginx -t "${BASE_IMAGE_NAME}-nginx:${TAG}" . || { echo "Nginx image build failed!"; exit 1; }
docker build -f back/mock_iiko_api/Dockerfile -t "${BASE_IMAGE_NAME}-mock_iiko:${TAG}" back/mock_iiko_api || { echo "Mock IIKO image build failed!"; exit 1; }

echo "All images built and tagged locally."

# --- Docker Network Definition ---
NETWORK_NAME="my_app_network"

# --- Cleanup (Optional, but good for fresh starts) ---
echo "Stopping and removing existing containers (ignoring 'no such container' errors)..."
CONTAINER_NAMES=("web" "scheduler" "bot" "nginx" "mock_iiko") # Added mock_iiko for cleanup
for name in "${CONTAINER_NAMES[@]}"; do
  docker stop "$name" > /dev/null 2>&1 || true # Suppress "no such container" output
  docker rm "$name" > /dev/null 2>&1 || true   # Suppress "no such container" output
done

echo "Removing the custom network if it exists..."
docker network rm "${NETWORK_NAME}" || true

# --- Create Network ---
echo "Creating Docker network..."
docker network create "${NETWORK_NAME}"

# --- 1. Start MySQL (DB) container ---
#echo "Starting DB container..."
#docker pull mysql:8.0 # This pulls from Docker Hub officially
#docker run -d --name db --network "${NETWORK_NAME}" \
#  -e "MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}" \
#  -e "MYSQL_DATABASE=${MYSQL_DATABASE}" \
#  -e "MYSQL_USER=${MYSQL_USER}" \
#  -e "MYSQL_PASSWORD=${MYSQL_PASSWORD}" \
#  -v db_data:/var/lib/mysql \
#  mysql:8.0

# --- 2. Start Web container (which runs migrations) ---
echo "Starting Web container..."
docker run -d --name web --network "${NETWORK_NAME}" \
  -p 8011:8011 \
  --env-file "${PROJECT_DIR}/.env" \
  -e "FLASK_APP=app" \
  -e "FLASK_ENV=production" \
  "${BASE_IMAGE_NAME}-web:${TAG}"

echo "Waiting for Web service to be up (implies migrations are done)..."
timeout 120 bash -c 'until nc -z localhost 8011; do sleep 2; done' || { echo 'Web service did not become available in time! Exiting.'; exit 1; }
echo "Web service is up."


# --- 3. Start Scheduler container ---
echo "Starting Scheduler container..."
docker run -d --name scheduler --network "${NETWORK_NAME}" \
  --env-file "${PROJECT_DIR}/.env" \
  "${BASE_IMAGE_NAME}-scheduler:${TAG}"

# --- 4. Start Bot container ---
echo "Starting Bot container..."
docker run -d --name bot --network "${NETWORK_NAME}" \
  --env-file "${PROJECT_DIR}/.env" \
  "${BASE_IMAGE_NAME}-bot:${TAG}"

# --- 5. Start Nginx container ---
#echo "Starting Nginx container..."
#docker run -d --name nginx --network "${NETWORK_NAME}" \
#  -p 80:8080 \
#  -p 443:8443 \
#  -v "${PROJECT_DIR}/nginx.conf:/etc/nginx/nginx.conf:ro" \
#  # If 'certs' moved to 'back/certs' and you want to volume mount, uncomment and adjust the path:
#  # -v "${PROJECT_DIR}/back/certs:/etc/nginx/certs:ro"
#  "${BASE_IMAGE_NAME}-nginx:${TAG}"

# --- 6. (Optional) Start Mock IIKO API container ---
echo "Starting Mock IIKO API container (if enabled)..."
# If you don't need this, you can comment out the lines below and remove "mock_iiko" from CONTAINER_NAMES
docker run -d --name mock_iiko --network "${NETWORK_NAME}" \
  -p 8080:8080 \
  --env-file "${PROJECT_DIR}/.env" \
  "${BASE_IMAGE_NAME}-mock_iiko:${TAG}"


echo "All containers started successfully."
