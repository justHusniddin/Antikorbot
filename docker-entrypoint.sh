#!/bin/bash
set -e
echo "== Container entrypoint: running migrations, collecting static, then starting supervisord =="

if [ -n "$POSTGRES_HOST" ] || [ -n "$POSTGRES_DB" ]; then
  DB_HOST="${POSTGRES_HOST:-db}"
  DB_PORT="${POSTGRES_PORT:-5432}"
  MAX_TRIES=20
  TRY=0
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "${POSTGRES_USER:-postgres}" >/dev/null 2>&1; do
      TRY=$((TRY+1))
      echo "Waiting for Postgres at $DB_HOST:$DB_PORT ($TRY/$MAX_TRIES)..."
      if [ "$TRY" -ge "$MAX_TRIES" ]; then
        echo "Postgres did not become ready in time. Exiting."
        exit 1
      fi
      sleep 2
  done
fi

if [ -n "$REDIS_HOST" ]; then
  R_HOST="${REDIS_HOST:-redis}"
  R_PORT="${REDIS_PORT:-6379}"
  MAX_TRIES=20
  TRY=0
  until redis-cli -h "$R_HOST" -p "$R_PORT" ping >/dev/null 2>&1; do
      TRY=$((TRY+1))
      echo "Waiting for Redis at $R_HOST:$R_PORT ($TRY/$MAX_TRIES)..."
      if [ "$TRY" -ge "$MAX_TRIES" ]; then
        echo "Redis did not become ready in time. Exiting."
        exit 1
      fi
      sleep 2
  done
fi

echo ">>> Running Django migrations..."
python manage.py makemigrations --noinput || true
python manage.py makemigrations tgbot --noinput || true
python manage.py migrate --noinput

echo ">>> Collecting static files..."
python manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo ">>> Creating superuser..."
  python manage.py createsuperuser --noinput || true
fi

echo ">>> Starting supervisord..."
exec "$@"
