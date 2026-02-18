set -eu
set -x

# Optional one-time ops (keep startup fast so Railway healthchecks pass).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

echo "Starting app. PORT=${PORT:-8080}"
python -c "import config.wsgi"  # fail fast with a real traceback in logs

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --log-level info \
  --access-logfile - \
  --error-logfile -
