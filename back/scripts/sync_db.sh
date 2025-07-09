source .env

docker compose run --rm \
  -e DATABASE_URL="mysql+pymysql://user:your_db_password@db:3306/mydatabase" \
  -e IIKO_API_URL="${IIKO_API_URL}" \
  -e IIKO_API_TOKEN="${IIKO_API_TOKEN}" \
  scheduler \
  python run_sync_once.py
