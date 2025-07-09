# Define your variables (replace with your actual values)
export CI_REGISTRY_IMAGE="your_gitlab_registry_path/your_project" # e.g., registry.gitlab.com/your_user/your_project_name
export TAG="latest" # Or the specific tag you want to deploy (e.g., dev-12345)

export DB_ROOT_PASSWORD="your_mysql_root_password"
export DB_NAME="your_database_name"
export DB_USER="your_db_user"
export DB_PASSWORD="your_db_password"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"

# IMPORTANT: PROJECT_DIR should be the root of your project where 'back/' and 'front/' reside.
# If you run 'start_app.sh' from the project root, $(pwd) is fine.
# If 'start_app.sh' is in 'back/', then you might need `export PROJECT_DIR=$(dirname $(pwd))`
export PROJECT_DIR=$(pwd)

# --- Start the sequence ---

set -e # Exit immediately if a command exits with a non-zero status

# Define network name
NETWORK_NAME=my_app_network

# --- Cleanup (Optional, but good for fresh starts) ---
echo "Stopping and removing existing containers..."
docker stop db web scheduler bot nginx || true
docker rm db web scheduler bot nginx || true

echo "Removing the custom network if it exists..."
docker network rm $NETWORK_NAME || true

# --- Create Network ---
echo "Creating Docker network..."
docker network create $NETWORK_NAME

# --- 1. Start MySQL (DB) container ---
echo "Starting DB container..."
docker pull mysql:8.0
docker run -d --name db --network $NETWORK_NAME \
  -e MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD} \
  -e MYSQL_DATABASE=${DB_NAME} \
  -e MYSQL_USER=${DB_USER} \
  -e MYSQL_PASSWORD=${DB_PASSWORD} \
  -v db_data:/var/lib/mysql \
  mysql:8.0

echo "Waiting for DB to be healthy..."
timeout 100 bash -c 'until docker exec db mysqladmin ping -h 127.0.0.1 -P 3306; do sleep 2; done' || { echo 'DB did not become healthy in time! Exiting.'; exit 1; }
echo "DB is healthy."

# --- 2. Start Web container (which runs migrations) ---
echo "Starting Web container..."
docker pull ${CI_REGISTRY_IMAGE}:${TAG}-web
docker run -d --name web --network $NETWORK_NAME \
  -p 8011:8011 \
  -e DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@db:3306/${DB_NAME} \
  -e FLASK_APP=app \
  -e FLASK_ENV=production \
  ${CI_REGISTRY_IMAGE}:${TAG}-web

echo "Waiting for Web service to be up (implies migrations are done)..."
timeout 120 bash -c 'until nc -z localhost 8011; do sleep 2; done' || { echo 'Web service did not become available in time! Exiting.'; exit 1; }
echo "Web service is up."


# --- 3. Start Scheduler container ---
echo "Starting Scheduler container..."
docker pull ${CI_REGISTRY_IMAGE}:${TAG}-scheduler
docker run -d --name scheduler --network $NETWORK_NAME \
  -e DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@db:3306/${DB_NAME} \
  ${CI_REGISTRY_IMAGE}:${TAG}-scheduler

# --- 4. Start Bot container ---
echo "Starting Bot container..."
docker pull ${CI_REGISTRY_IMAGE}:${TAG} # Assuming this is your bot image
docker run -d --name bot --network $NETWORK_NAME \
  -e TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN} \
  -e DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASSWORD}@db:3306/${DB_NAME} \
  ${CI_REGISTRY_IMAGE}:${TAG}

# --- 5. Start Nginx container ---
echo "Starting Nginx container..."
docker pull ${CI_REGISTRY_IMAGE}:${TAG}-nginx
docker run -d --name nginx --network $NETWORK_NAME \
  -p 80:8080 \
  -p 443:8443 \
  -v ${PROJECT_DIR}/nginx.conf:/etc/nginx/nginx.conf:ro \
  # If 'certs' moved to 'back/certs' and you want to volume mount, adjust the path:
  # -v ${PROJECT_DIR}/back/certs:/etc/nginx/certs:ro \
  ${CI_REGISTRY_IMAGE}:${TAG}-nginx

echo "All containers started successfully."
