# ─── SubTerra Development Container ────────────────────────────────────
# Based on FEniCS so simulations can run locally (QUEUE_CONNECTION=sync).
# Also includes PHP + Node.js for the Laravel + Vue frontend.
#
# In PRODUCTION the architecture is split:
#   - backend container:  PHP + Node (docker/backend/Dockerfile, lightweight)
#   - fenics container:   FEniCS only  (docker/fenics/Dockerfile, heavy)
# See docker-compose.yml for the production layout.
# ───────────────────────────────────────────────────────────────────────

FROM ghcr.io/scientificcomputing/fenics-gmsh:2024-05-30

# ── PHP 8.1 + extensions ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:ondrej/php -y \
    && apt-get update && apt-get install -y \
    php8.1-cli \
    php8.1-mbstring \
    php8.1-xml \
    php8.1-curl \
    php8.1-sqlite3 \
    php8.1-bcmath \
    php8.1-zip \
    unzip \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# ── Composer ──────────────────────────────────────────────────────────
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# ── Node.js 20 ───────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────────────
WORKDIR /home/SubTerra
COPY requirements.txt /home/SubTerra/requirements.txt
RUN pip install -r requirements.txt

CMD ["/bin/bash"]