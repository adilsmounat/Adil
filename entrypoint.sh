set -eu

# Optional one-time ops (keep startup fast so Railway healthchecks pass).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8080}"
