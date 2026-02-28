# ─── Stage 1: Build frontend assets ────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /build
COPY backend/package.json backend/package-lock.json* backend/vite.config.js ./
RUN npm ci
COPY backend/resources/ ./resources/
RUN npm run build

# ─── Stage 2: Laravel Backend ──────────────────────────────────────────
FROM php:8.2-cli

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg \
    libpng-dev \
    libonig-dev \
    libxml2-dev \
    zip \
    unzip \
    sqlite3 \
    libsqlite3-dev \
    supervisor \
    && docker-php-ext-install pdo pdo_mysql pdo_sqlite mbstring xml bcmath \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI only (no daemon — we talk to the host's Docker socket)
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Copy Laravel application
COPY backend/ /var/www/html/

# Copy pre-built frontend assets from stage 1
COPY --from=frontend /build/public/build/ /var/www/html/public/build/

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader --no-interaction

# Generate .env from example (the real .env is excluded by .dockerignore).
# Runtime environment variables from docker-compose override these defaults.
RUN cp .env.example .env \
    && sed -i 's/DB_CONNECTION=mysql/DB_CONNECTION=sqlite/' .env \
    && sed -i 's|DB_HOST=.*|#DB_HOST=|' .env \
    && sed -i 's|DB_DATABASE=.*|DB_DATABASE=/var/www/html/database/database.sqlite|' .env \
    && php artisan key:generate --force

# Create SQLite database, run migrations, set permissions
RUN touch /var/www/html/database/database.sqlite \
    && php artisan migrate --force \
    && chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache /var/www/html/database

# Ensure the jobs directory exists
RUN mkdir -p /var/www/html/storage/app/jobs

# Copy supervisor configuration
COPY docker/backend/supervisord.conf /etc/supervisor/conf.d/subterra.conf

# Copy entrypoint that syncs docker-compose env vars into .env
COPY docker/backend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/subterra.conf"]
