#!/bin/bash
set -e

# ─── Backend Container Entrypoint ─────────────────────────────────────
# Writes runtime environment variables (from docker-compose) into the
# Laravel .env file so that supervisord child processes (artisan serve,
# queue workers) see them.  supervisord does not pass its own environment
# to child programs by default.

ENV_FILE="/var/www/html/.env"

# Helper: set or update a key in .env
set_env() {
    local key="$1" val="$2"
    if [ -z "$val" ]; then return; fi
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

# Patch .env with docker-compose environment overrides
set_env APP_NAME       "${APP_NAME}"
set_env APP_ENV        "${APP_ENV}"
set_env APP_DEBUG      "${APP_DEBUG}"
set_env APP_URL        "${APP_URL}"
set_env DB_CONNECTION  "${DB_CONNECTION}"
set_env DB_DATABASE    "${DB_DATABASE}"
set_env QUEUE_CONNECTION "${QUEUE_CONNECTION}"
set_env REDIS_HOST     "${REDIS_HOST}"
set_env REDIS_PORT     "${REDIS_PORT}"
set_env CACHE_DRIVER   "${CACHE_DRIVER}"
set_env SESSION_DRIVER "${SESSION_DRIVER}"

# SubTerra-specific
set_env SUBTERRA_RUNNER_MODE        "${SUBTERRA_RUNNER_MODE}"
set_env SUBTERRA_FENICS_IMAGE       "${SUBTERRA_FENICS_IMAGE}"
set_env SUBTERRA_DOCKER_JOBS_VOLUME "${SUBTERRA_DOCKER_JOBS_VOLUME}"
set_env SUBTERRA_PROJECT_ROOT       "${SUBTERRA_PROJECT_ROOT}"

# Ensure storage + cache dirs are writable
chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache 2>/dev/null || true

# Run pending migrations (idempotent)
php /var/www/html/artisan migrate --force 2>/dev/null || true

exec "$@"
