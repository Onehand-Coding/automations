"""Devops scaffolding for generated fullstack/flutter projects.

Emits the devops layer shared by Kenneth's apps (resident-hub, pwdims,
aics-tracking-system, seniorhub, solo-parent-hub, muni-track, maco-website):

- always: ./dev, CI workflow (.github/workflows/ci.yml), image Dockerfiles
  (--local=False uses a plain-HTTP nginx conf; CI publishes to ghcr either way)
- --local adds: ./prod, docker-compose.prod.yml, .env.prod.example and the
  TLS nginx conf for LAN boxes where staff reach the app by IP — hence the
  self-signed certificate issued for the host's LAN IP. A public/VPS
  deployment needs real certificates (Caddy or nginx + Let's Encrypt against
  a domain), so `prod tls` and `prod deploy` here do NOT transfer to that case.

The rules these templates encode live in ~/Coding/projects/standards
(docs/local-deploy-standard.md); scripts/check-deploy-parity.sh there audits a
repo against them. Update that doc when a template change encodes a new rule.

Templates are plain strings with __TOKEN__ placeholders rather than f-strings:
shell and YAML are dense with braces, and doubling every one of them is a
reliable source of bugs.
"""

import stat
from pathlib import Path

try:
    from automations_cli.versions import (
        FLUTTER_BUILD_IMAGE,
        NODE_DOCKER_IMAGE,
        NODE_ENGINES,
        NODE_MAJOR,
    )
except ImportError:  # imported as a top-level module via sys.path.append
    from versions import FLUTTER_BUILD_IMAGE, NODE_DOCKER_IMAGE, NODE_ENGINES, NODE_MAJOR


def _write(path: Path, content: str, project_name: str, executable: bool = False):
    package_name = project_name.replace("-", "_")
    rendered = (
        content.replace("__PROJECT__", project_name)
        .replace("__PACKAGE__", package_name)
        .replace("__NODE_MAJOR__", NODE_MAJOR)
        .replace("__NODE_ENGINES__", NODE_ENGINES)
        .replace("__NODE_DOCKER_IMAGE__", NODE_DOCKER_IMAGE)
        .replace("__FLUTTER_BUILD_IMAGE__", FLUTTER_BUILD_IMAGE)
        .lstrip("\n")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"[OK] Created: {path}")


DEV_SCRIPT = """
#!/bin/bash
# Dev environment manager

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Job control on: each `&` background job gets its own process group, so
# `kill -PID` (below) reaches that job's whole subtree — e.g. uvicorn's
# --reload supervisor *and* its forked worker — instead of just the top
# process and orphaning the rest.
set -m

case "${1:-}" in
    db-up)
        echo "Starting PostgreSQL..."
        cd "$ROOT_DIR" && docker compose up -d
        echo "DB ready on localhost:5432"
        ;;
    db-down)
        echo "Stopping PostgreSQL..."
        cd "$ROOT_DIR" && docker compose down
        echo "DB stopped."
        ;;
    logs)
        # Dev containers only (db). The backend/frontend run bare-metal and
        # log to the terminal that started them.
        cd "$ROOT_DIR" && docker compose logs -f "${2:-}"
        ;;
    status)
        cd "$ROOT_DIR" && docker compose ps
        PID_FILE="$ROOT_DIR/.__PACKAGE__.pids"
        if [ -f "$PID_FILE" ]; then
            source "$PID_FILE"
            echo ""
            echo "Bare-metal processes (from $(basename "$PID_FILE")):"
            for entry in "backend:$BACKEND_PID" "frontend:$FRONTEND_PID"; do
                name="${entry%%:*}"; pid="${entry##*:}"
                if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                    echo "  $name   running (PID $pid)"
                else
                    echo "  $name   not running (stale PID ${pid:-none})"
                fi
            done
        fi
        ;;
    nuke)
        echo "Removing all containers and volumes..."
        cd "$ROOT_DIR" && docker compose down -v
        echo "All containers and volumes removed."
        ;;
    backup)
        BACKUP_DIR="$ROOT_DIR/backups/dev"
        TIMESTAMP=$(date +%F_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/__PACKAGE___${TIMESTAMP}.sql.gz"
        RETENTION_DAYS=30

        mkdir -p "$BACKUP_DIR"

        cd "$ROOT_DIR"
        docker compose exec -T db pg_dump -U postgres __PACKAGE__ | gzip > "$BACKUP_FILE"

        echo "Backup written: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
        find "$BACKUP_DIR" -name "__PACKAGE___*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
        echo "Backup complete. $(find "$BACKUP_DIR" -name '__PACKAGE___*.sql.gz' | wc -l) backups retained."
        ;;
    restore)
        BACKUP_DIR="$ROOT_DIR/backups/dev"

        if [ -n "${2:-}" ]; then
            BACKUP_FILE="$2"
        else
            BACKUP_FILE=$(ls -t "$BACKUP_DIR"/__PACKAGE___*.sql.gz 2>/dev/null | head -1)
        fi

        if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
            echo "No backup found. Run './dev backup' first, or pass a path: ./dev restore file.sql.gz"
            exit 1
        fi

        echo "Restoring from: $BACKUP_FILE"
        cd "$ROOT_DIR"
        gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U postgres __PACKAGE__
        echo "Restore complete."
        ;;
    "")
        echo "Starting __PROJECT__..."

        BACKEND_DIR="$ROOT_DIR/backend"
        FRONTEND_DIR="$ROOT_DIR/frontend"

        echo "Cleaning up existing processes..."

        PID_FILE="$ROOT_DIR/.__PACKAGE__.pids"
        BACKEND_PID=""
        FRONTEND_PID=""

        # Signals the whole process group (PGID == PID for a `set -m`
        # background job), not just the leader — so uvicorn's --reload
        # supervisor and its forked worker both go down together.
        graceful_kill() {
            local pid=$1
            local name=$2
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                echo "   Sending SIGTERM to $name's process group (PGID: $pid)..."
                kill -TERM -"$pid" 2>/dev/null
                for i in 1 2 3 4 5; do
                    sleep 1
                    if ! kill -0 "$pid" 2>/dev/null; then
                        echo "   $name stopped gracefully"
                        return 0
                    fi
                done
                echo "   Force-stopping $name's process group..."
                kill -KILL -"$pid" 2>/dev/null
            fi
            return 0
        }

        if [ -f "$PID_FILE" ]; then
            source "$PID_FILE"
            [ -n "$BACKEND_PID" ] && graceful_kill "$BACKEND_PID" "backend"
            [ -n "$FRONTEND_PID" ] && graceful_kill "$FRONTEND_PID" "frontend"
            rm -f "$PID_FILE"
        fi

        pkill -15 -f 'uvicorn.*__PACKAGE__' 2>/dev/null
        pkill -15 -f '__FRONTEND_PKILL__' 2>/dev/null

        sleep 1
        echo "Cleanup complete"
        echo ""

        # DB is optional: projects generated without --compose run on SQLite.
        if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
            echo "Starting PostgreSQL..."
            cd "$ROOT_DIR"
            docker compose up -d

            DB_CONTAINER=$(docker compose ps -q db)
            for _ in $(seq 1 30); do
                docker exec "$DB_CONTAINER" pg_isready -U postgres >/dev/null 2>&1 && break
                sleep 1
            done

            # Alembic owns the schema once initialized; starting the backend
            # against a stale schema produces errors that look like app bugs.
            # Projects that have not run `alembic-init` yet skip this.
            if [ -f "$BACKEND_DIR/alembic.ini" ]; then
                echo "Applying database migrations..."
                (cd "$BACKEND_DIR" && uv run db-upgrade) || {
                    echo "Migration failed — fix it before starting (./dev db-down to stop the DB)." >&2
                    exit 1
                }
                echo "Database up to date"
            fi

            echo "DB ready"
            echo ""
        fi

        cleanup() {
            echo ""
            echo "Shutting down..."
            graceful_kill "$BACKEND_PID" "backend"
            graceful_kill "$FRONTEND_PID" "frontend"
            # Backstop: catches anything that escaped its process group.
            pkill -15 -f 'uvicorn.*__PACKAGE__' 2>/dev/null
            pkill -15 -f '__FRONTEND_PKILL__' 2>/dev/null
            if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
                cd "$ROOT_DIR" && docker compose down
            fi
            exit 0
        }

        trap cleanup SIGINT SIGTERM

        echo "Starting backend..."
        cd "$BACKEND_DIR"
        uv run dev &
        BACKEND_PID=$!
        echo "Backend running on http://localhost:8000"

        sleep 2

        echo "Starting frontend..."
        cd "$FRONTEND_DIR"
        __FRONTEND_CMD__ &
        FRONTEND_PID=$!
        echo "Frontend running on http://localhost:5173"
        echo ""

        cat > "$PID_FILE" << EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF

        echo "------------------------------------"
        echo "  Backend:  http://localhost:8000"
        echo "  Frontend: http://localhost:5173"
        echo "  API Docs: http://localhost:8000/docs"
        echo "------------------------------------"
        echo ""
        echo "Press Ctrl+C to stop all servers"
        echo ""

        wait $BACKEND_PID $FRONTEND_PID
        ;;
    *)
        echo "Usage: ./dev [command]"
        echo ""
        echo "Commands:"
        echo "  (none)      Start everything — DB (if compose exists), backend, frontend"
        echo "  db-up       Start only the PostgreSQL container"
        echo "  db-down     Stop the PostgreSQL container"
        echo "  logs        Tail dev container logs (optional: ./dev logs db)"
        echo "  status      Show dev container + bare-metal process status"
        echo "  backup      Dump dev database to a gzipped SQL file"
        echo "  restore     Restore from latest backup (or path: ./dev restore file.sql.gz)"
        echo "  nuke        Stop and remove everything including volumes"
        exit 1
        ;;
esac
"""


PROD_SCRIPT = """
#!/bin/bash
set -e

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read one key out of .env.prod. Deliberately NOT `set -a; . .env.prod` —
# that file is docker-compose syntax, not shell, so an unquoted value with
# a space makes bash run the second word as a command, which under `set -e`
# kills the script. Sourcing it would also execute any $(...) in a value.
env_get() {
    [ -f "$REPO_DIR/.env.prod" ] || return 0
    sed -n "s/^$1=//p" "$REPO_DIR/.env.prod" | head -1
}

usage() {
    echo "Usage: ./prod <command>"
    echo ""
    echo "Commands:"
    echo "  deploy    Generate TLS cert (if missing), pull latest images, and start services"
    echo "  build     Build images from source"
    echo "  pull      Pull latest images from the registry"
    echo "  up        Start containers (no build, no pull)"
    echo "  down      Stop and remove containers (data preserved)"
    echo "  nuke      Stop and remove everything including volumes"
    echo "  logs      Tail logs (default: backend)"
    echo "  status    Show container status"
    echo "  backup    Dump the database to a compressed file"
    echo "  restore   Restore from latest backup (or path: ./prod restore file.sql.gz)"
    echo "  offsite-sync   Rsync ./backups to OFFSITE_TARGET (set in .env.prod)"
    echo "  tls       Regenerate the self-signed TLS certificate"
    exit 1
}

[[ $# -lt 1 ]] && usage

case "$1" in
    deploy)
        LAN_IP=$(ip addr show | grep "inet " | grep -v 127.0.0.1 \\
          | awk '{print $2}' | cut -d'/' -f1 | head -1)
        CERT_FILE="$REPO_DIR/frontend/certs/__PROJECT__.crt"
        CERT_CN=$(openssl x509 -in "$CERT_FILE" -noout -subject 2>/dev/null \\
          | sed -n 's/.*CN=\\([^/]*\\).*/\\1/p')
        if [ -f "$CERT_FILE" ] && [ "$CERT_CN" = "$LAN_IP" ]; then
            echo "TLS certificate exists and matches $LAN_IP — keeping it (regenerate via ./prod tls)"
        else
            "$REPO_DIR/prod" tls "$LAN_IP"
        fi
        "$REPO_DIR/prod" pull
        "$REPO_DIR/prod" up
        ;;
    build)
        echo "Building images from source..."
        $COMPOSE build
        ;;
    pull)
        echo "Pulling latest images..."
        $COMPOSE pull --ignore-pull-failures
        ;;
    up)
        # .env.prod holds BACKUP_ENCRYPTION_PASSPHRASE, the DB password and
        # every app secret. cp .env.prod.example .env.prod under the default
        # umask 022 creates it world-readable, and these apps share one office
        # box. Enforced on every `up` rather than fixed once: the next fresh
        # clone recreates the same 0644 file. `if`, not `[ -f ] && chmod`:
        # under set -e the && form exits the whole script when the file is
        # absent, swallowing compose's much more useful "POSTGRES_PASSWORD is
        # required" error.
        if [ -f "$REPO_DIR/.env.prod" ]; then
            chmod 600 "$REPO_DIR/.env.prod"
        fi

        # Create ./backups before compose runs. If a bind-mount source does not
        # exist, the Docker daemon creates it as root:root, and backup sidecars
        # running as HOST_UID:HOST_GID cannot write into it — they sit
        # unhealthy logging "Permission denied" while zero backups exist.
        mkdir -p "$REPO_DIR/backups"
        chown "$(id -u):$(id -g)" "$REPO_DIR/backups"
        export HOST_UID="$(id -u)" HOST_GID="$(id -g)"

        echo "Starting production stack..."
        $COMPOSE up -d
        $COMPOSE ps
        ;;
    down)
        $COMPOSE down
        ;;
    nuke)
        echo "This removes all containers AND volumes (database included)."
        read -r -p "Type the project name to confirm: " confirm
        [ "$confirm" = "__PROJECT__" ] || { echo "Aborted."; exit 1; }
        $COMPOSE down -v
        ;;
    logs)
        $COMPOSE logs -f "${2:-backend}"
        ;;
    status)
        $COMPOSE ps
        ;;
    backup)
        # Encrypted at rest. A dump on an office-LAN box is the whole
        # database in one readable file; umask 077 keeps it off other
        # accounts, openssl keeps it unreadable if the file itself walks.
        export BACKUP_ENCRYPTION_PASSPHRASE="$(env_get BACKUP_ENCRYPTION_PASSPHRASE)"
        : "${BACKUP_ENCRYPTION_PASSPHRASE:?set BACKUP_ENCRYPTION_PASSPHRASE in .env.prod}"

        BACKUP_DIR="$REPO_DIR/backups"
        TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
        RETENTION_DAYS="$(env_get BACKUP_RETENTION_DAYS)"
        RETENTION_DAYS="${RETENTION_DAYS:-30}"

        umask 077
        mkdir -p "$BACKUP_DIR"

        DB_FILE="$BACKUP_DIR/__PACKAGE__-manual-${TIMESTAMP}.sql.gz.enc"
        $COMPOSE up -d --wait db
        $COMPOSE exec -T db pg_dump -U postgres __PACKAGE__ \\
          | gzip \\
          | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_PASSPHRASE > "$DB_FILE"
        if [ "${PIPESTATUS[0]}" -ne 0 ]; then
            echo "Backup failed: pg_dump did not complete (is the db container running?)" >&2
            rm -f "$DB_FILE"
            exit 1
        fi
        echo "Database backup: $DB_FILE ($(du -h "$DB_FILE" | cut -f1))"

        find "$BACKUP_DIR" -name '__PACKAGE__-manual-*.sql.gz.enc' -mtime "+${RETENTION_DAYS}" -delete
        echo "Backup complete."
        ;;
    restore)
        export BACKUP_ENCRYPTION_PASSPHRASE="$(env_get BACKUP_ENCRYPTION_PASSPHRASE)"
        : "${BACKUP_ENCRYPTION_PASSPHRASE:?set BACKUP_ENCRYPTION_PASSPHRASE in .env.prod}"

        BACKUP_DIR="$REPO_DIR/backups"
        if [ -n "${2:-}" ]; then
            BACKUP_FILE="$2"
        else
            BACKUP_FILE=$(ls -t "$BACKUP_DIR"/__PACKAGE__-manual-*.sql.gz.enc 2>/dev/null | head -1)
        fi

        if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
            echo "No backup found. Run './prod backup' first, or pass a path."
            exit 1
        fi

        echo "This OVERWRITES the production database from $BACKUP_FILE."
        read -r -p "Type the project name to confirm: " confirm
        [ "$confirm" = "__PROJECT__" ] || { echo "Aborted."; exit 1; }

        DB_TMP=$(mktemp /tmp/__PACKAGE__-restore-XXXXXX.sql)
        trap 'rm -f "$DB_TMP"' EXIT

        echo "Verifying backup before touching the live database..."
        # The live DB is dropped below — never get there with an unreadable
        # backup. Decrypt + decompress to a temp file first: a wrong
        # passphrase or corrupt archive fails here, while the DB is intact.
        openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_ENCRYPTION_PASSPHRASE \\
            -in "$BACKUP_FILE" | gunzip -c > "$DB_TMP"

        if [ ! -s "$DB_TMP" ] || ! head -n 5 "$DB_TMP" | grep -q "PostgreSQL database dump"; then
            echo "ERROR: Backup does not look like a valid PostgreSQL dump (wrong passphrase or corrupt file). Aborting — nothing was changed." >&2
            exit 1
        fi

        echo "Backup verified. Recreating __PACKAGE__..."
        $COMPOSE up -d --wait db
        $COMPOSE exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS __PACKAGE__;"
        $COMPOSE exec -T db psql -U postgres -d postgres -c "CREATE DATABASE __PACKAGE__ OWNER postgres;"
        $COMPOSE exec -T db psql -U postgres -d __PACKAGE__ < "$DB_TMP"
        echo "Restore complete."
        ;;
    offsite-sync)
        BACKUP_DIR="$REPO_DIR/backups"
        OFFSITE_TARGET="$(env_get OFFSITE_TARGET)"
        if [ -z "${OFFSITE_TARGET:-}" ]; then
            echo "OFFSITE_TARGET is not set in .env.prod — nothing to sync to." >&2
            echo "Set OFFSITE_TARGET=user@host:/path/ in .env.prod first." >&2
            exit 1
        fi
        rsync -az --delete "$BACKUP_DIR/" "$OFFSITE_TARGET"
        echo "Offsite sync complete."
        ;;
    tls)
        CERT_DIR="$REPO_DIR/frontend/certs"
        LAN_IP="${2:-$(ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d'/' -f1 | head -1)}"

        mkdir -p "$CERT_DIR"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
          -keyout "$CERT_DIR/__PROJECT__.key" \\
          -out "$CERT_DIR/__PROJECT__.crt" \\
          -subj "/CN=$LAN_IP" \\
          -addext "subjectAltName=IP:$LAN_IP,DNS:localhost"

        echo "Certificate generated for CN=$LAN_IP at $CERT_DIR"
        echo "Staff browsers must accept this self-signed cert on first visit."
        ;;
    *)
        usage
        ;;
esac
"""


PROD_COMPOSE = """
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env.prod}"
      POSTGRES_DB: __PACKAGE__
    volumes:
      - pgdata_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks: [__PACKAGE__net]

  backend:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env.prod}@db:5432/__PACKAGE__
      SECRET_KEY: "${SECRET_KEY:?set SECRET_KEY in .env.prod}"
      DEBUG: "False"
    depends_on:
      db:
        condition: service_healthy
    networks: [__PACKAGE__net]

  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./frontend/certs:/etc/nginx/certs:ro
    depends_on:
      - backend
    networks: [__PACKAGE__net]

networks:
  __PACKAGE__net:

volumes:
  pgdata_prod:
"""


ENV_PROD_EXAMPLE = """
# Production secrets for __PROJECT__. Copy to .env.prod and fill in.
# .env.prod is gitignored — never commit real values.
#
# Generate strong values with: openssl rand -base64 32

POSTGRES_PASSWORD=
SECRET_KEY=

# Passphrase for at-rest encryption of `./prod backup` dumps
# (openssl aes-256-cbc). Required — backup and restore both refuse to run
# without it. Generate with: openssl rand -base64 36
# LOSING THIS MEANS LOSING EVERY BACKUP: an encrypted dump cannot be
# recovered without it, so keep a copy somewhere durable off this machine.
BACKUP_ENCRYPTION_PASSPHRASE=

# Retention for `./prod backup` dumps, in days.
BACKUP_RETENTION_DAYS=30

# Optional: rsync target for `./prod offsite-sync`, e.g. user@host:/backups/
OFFSITE_TARGET=
"""


BACKEND_DOCKERFILE = """
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    UV_COMPILE_BYTECODE=1 \\
    UV_LINK_MODE=copy \\
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "start"]
"""


FRONTEND_DOCKERFILE = """
FROM __NODE_DOCKER_IMAGE__ AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY __NGINX_CONF__ /etc/nginx/conf.d/default.conf
EXPOSE 80 443
"""


FLUTTER_FRONTEND_DOCKERFILE = """
FROM __FLUTTER_BUILD_IMAGE__ AS build

WORKDIR /app
COPY . .
RUN flutter pub get && flutter build web

FROM nginx:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
COPY __NGINX_CONF__ /etc/nginx/conf.d/default.conf
EXPOSE 80 443
"""


NGINX_CONF = """
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: unknown paths fall through to index.html.
    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""


NGINX_TLS_CONF = """
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/certs/__PROJECT__.crt;
    ssl_certificate_key /etc/nginx/certs/__PROJECT__.key;

    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: unknown paths fall through to index.html.
    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""


CI_WORKFLOW_REACT = """
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: onehand-coding/__PROJECT__

permissions:
  contents: read

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python
        run: uv python install 3.12

      # Single owner of dependency scanning for both trees (dev deps included
      # — build tooling ships nothing, but a compromised vite compromises the
      # artifact it produces). Never add a second npm/pip audit elsewhere under
      # different flags: two verdicts on one lockfile reads as noise.
      - name: Install backend deps (for pip-audit)
        working-directory: backend
        run: uv sync --frozen

      - name: pip-audit
        working-directory: backend
        run: |
          uv pip install pip-audit
          uv run pip-audit --skip-editable

      - name: Set up Node.js
        uses: actions/setup-node@v7
        with:
          node-version: "__NODE_MAJOR__"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend deps
        working-directory: frontend
        run: npm ci

      - name: npm audit
        working-directory: frontend
        run: |
          # npm audit exits non-zero on *any* finding, including allow-listed
          # ones, so it must not short-circuit before check-audit.cjs applies
          # the allow-list.
          npm audit --json > audit-result.json || true
          node scripts/check-audit.cjs < audit-result.json

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        working-directory: backend
        run: uv sync --frozen

      - name: Run tests
        working-directory: backend
        run: uv run pytest -v

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7

      - name: Set up Node.js
        uses: actions/setup-node@v7
        with:
          node-version: "__NODE_MAJOR__"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm run test

      - name: Type-check + build
        run: npm run build

  image-scan:
    # OS-layer scan of the built images; complements the security job, which
    # owns the Python/npm dependency trees. Built via buildx with a GHA cache
    # export (same scope build-and-push reads from) so the image cd publishes
    # is a cache-hit reproduction of *this exact* scanned image, not a fresh
    # rebuild from source that Trivy never saw.
    needs: [security, backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Build backend image
        uses: docker/build-push-action@v7
        with:
          context: ./backend
          push: false
          load: true
          tags: __PROJECT__-backend:ci
          cache-from: type=gha,scope=backend-image
          cache-to: type=gha,mode=max,scope=backend-image

      - name: Scan backend image for CRITICAL vulnerabilities (blocking)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-backend:ci
          format: table
          severity: CRITICAL
          exit-code: "1"
          ignore-unfixed: true

      - name: Scan backend image for HIGH vulnerabilities (report only)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-backend:ci
          format: table
          severity: HIGH
          exit-code: "0"
          ignore-unfixed: true

      - name: Build frontend image
        uses: docker/build-push-action@v7
        with:
          context: ./frontend
          push: false
          load: true
          tags: __PROJECT__-frontend:ci
          cache-from: type=gha,scope=frontend-image
          cache-to: type=gha,mode=max,scope=frontend-image

      - name: Scan frontend image for CRITICAL vulnerabilities (blocking)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-frontend:ci
          format: table
          severity: CRITICAL
          exit-code: "1"
          ignore-unfixed: true

      - name: Scan frontend image for HIGH vulnerabilities (report only)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-frontend:ci
          format: table
          severity: HIGH
          exit-code: "0"
          ignore-unfixed: true

  cd:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: [image-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v7

      - name: Log in to GHCR
        uses: docker/login-action@v4
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v7
        with:
          context: ./backend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:latest
          cache-from: type=gha,scope=backend-image
          cache-to: type=gha,mode=max,scope=backend-image

      - name: Build and push frontend
        uses: docker/build-push-action@v7
        with:
          context: ./frontend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:latest
          cache-from: type=gha,scope=frontend-image
          cache-to: type=gha,mode=max,scope=frontend-image
"""


CI_WORKFLOW_FLUTTER = """
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: onehand-coding/__PROJECT__

permissions:
  contents: read

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python
        run: uv python install 3.12

      - name: Install backend deps (for pip-audit)
        working-directory: backend
        run: uv sync --frozen

      - name: pip-audit
        working-directory: backend
        run: |
          uv pip install pip-audit
          uv run pip-audit --skip-editable

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        working-directory: backend
        run: uv sync --frozen

      - name: Run tests
        working-directory: backend
        run: uv run pytest -v

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7

      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: stable

      - name: Install dependencies
        run: flutter pub get

      - name: Analyze
        run: flutter analyze

      - name: Test
        run: flutter test

      - name: Build web
        run: flutter build web

  image-scan:
    # OS-layer scan of the built images; complements the security job, which
    # owns the Python/npm dependency trees. Built via buildx with a GHA cache
    # export (same scope build-and-push reads from) so the image cd publishes
    # is a cache-hit reproduction of *this exact* scanned image, not a fresh
    # rebuild from source that Trivy never saw.
    needs: [security, backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Build backend image
        uses: docker/build-push-action@v7
        with:
          context: ./backend
          push: false
          load: true
          tags: __PROJECT__-backend:ci
          cache-from: type=gha,scope=backend-image
          cache-to: type=gha,mode=max,scope=backend-image

      - name: Scan backend image for CRITICAL vulnerabilities (blocking)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-backend:ci
          format: table
          severity: CRITICAL
          exit-code: "1"
          ignore-unfixed: true

      - name: Scan backend image for HIGH vulnerabilities (report only)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-backend:ci
          format: table
          severity: HIGH
          exit-code: "0"
          ignore-unfixed: true

      - name: Build frontend image
        uses: docker/build-push-action@v7
        with:
          context: ./frontend
          push: false
          load: true
          tags: __PROJECT__-frontend:ci
          cache-from: type=gha,scope=frontend-image
          cache-to: type=gha,mode=max,scope=frontend-image

      - name: Scan frontend image for CRITICAL vulnerabilities (blocking)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-frontend:ci
          format: table
          severity: CRITICAL
          exit-code: "1"
          ignore-unfixed: true

      - name: Scan frontend image for HIGH vulnerabilities (report only)
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: __PROJECT__-frontend:ci
          format: table
          severity: HIGH
          exit-code: "0"
          ignore-unfixed: true

  cd:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: [image-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v7

      - name: Log in to GHCR
        uses: docker/login-action@v4
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v7
        with:
          context: ./backend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:latest
          cache-from: type=gha,scope=backend-image
          cache-to: type=gha,mode=max,scope=backend-image

      - name: Build and push frontend
        uses: docker/build-push-action@v7
        with:
          context: ./frontend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:latest
          cache-from: type=gha,scope=frontend-image
          cache-to: type=gha,mode=max,scope=frontend-image
"""


CHECK_AUDIT_CJS = """
#!/usr/bin/env node
// Fails CI on any high/critical advisory that isn't on the small, reviewed
// allow-list below. Reads `npm audit --json` from stdin — see the "npm audit"
// step of the `security` job in .github/workflows/ci.yml.
//
// Native `npm audit --audit-level=high` has no way to allow-list a specific
// known/accepted advisory, so a blanket severity gate lets real high-severity
// issues through indefinitely. This keeps the gate strict while tracking
// today's reviewed exceptions explicitly, rather than silently.
//
// Shared verbatim across the sibling repos; only ALLOWED_GHSA_IDS and its
// rationale comment are per-app. Keep the logic in sync when changing any copy.
const fs = require("fs");
const data = JSON.parse(fs.readFileSync(0, "utf8"));

// Empty by design: a freshly generated project starts clean. When an advisory
// lands that you have reviewed and accepted, add its GHSA id here WITH the
// rationale (what exposes you, why it does not apply to this app, and what
// upstream fix would let you remove it). An allow-list entry without a
// rationale is how gates rot.
const ALLOWED_GHSA_IDS = new Set([]);

const vulnerabilities = data.vulnerabilities || {};
const unexpected = [];

for (const pkg of Object.values(vulnerabilities)) {
  if (pkg.severity !== "high" && pkg.severity !== "critical") continue;
  for (const via of pkg.via || []) {
    if (typeof via !== "object" || !via.url) continue;
    const match = via.url.match(/advisories\\/(GHSA-[a-z0-9-]+)/i);
    const id = match ? match[1] : via.url;
    if (!ALLOWED_GHSA_IDS.has(id)) {
      unexpected.push(`${pkg.name}: ${via.title} (${id}, severity=${pkg.severity})`);
    }
  }
}

if (unexpected.length > 0) {
  console.error("Unexpected high/critical vulnerabilities (not on the reviewed allow-list):");
  for (const line of unexpected) console.error(`  - ${line}`);
  process.exit(1);
}
console.log("No unexpected high/critical vulnerabilities (allow-listed advisories only, if any).");
"""


def scaffold_devops(root: Path, project_name: str, flavor: str = "react", local: bool = False):
    """Emit the devops layer: ./dev always; ./prod + prod stack when local=True.

    Also always emits CI (.github/workflows/ci.yml), the audit gate script and
    the image Dockerfiles, so a freshly generated repo is CI-green and
    publishable to ghcr on day one.

    flavor: "react" (npm/vite frontend) or "flutter" (flutter run frontend).
    """
    if flavor == "react":
        dev_script = DEV_SCRIPT.replace("__FRONTEND_CMD__", "npm run dev").replace(
            "__FRONTEND_PKILL__", "vite.*frontend"
        )
        ci_workflow = CI_WORKFLOW_REACT
    elif flavor == "flutter":
        dev_script = DEV_SCRIPT.replace("__FRONTEND_CMD__", "flutter run -d chrome").replace(
            "__FRONTEND_PKILL__", "flutter_tools"
        )
        ci_workflow = CI_WORKFLOW_FLUTTER
    else:
        raise ValueError(f"Unknown flavor: {flavor!r} (expected 'react' or 'flutter')")

    _write(root / "dev", dev_script, project_name, executable=True)
    _write(root / ".github" / "workflows" / "ci.yml", ci_workflow, project_name)

    if flavor == "react":
        _write(root / "frontend" / "scripts" / "check-audit.cjs", CHECK_AUDIT_CJS, project_name)

    nginx_conf = "nginx-tls.conf" if local else "nginx.conf"
    _write(root / "nginx.conf", NGINX_CONF, project_name)
    if local:
        _write(root / "nginx-tls.conf", NGINX_TLS_CONF, project_name)

    if flavor == "react":
        _write(
            root / "frontend" / "Dockerfile",
            FRONTEND_DOCKERFILE.replace("__NGINX_CONF__", nginx_conf),
            project_name,
        )
    else:
        _write(
            root / "frontend" / "Dockerfile",
            FLUTTER_FRONTEND_DOCKERFILE.replace("__NGINX_CONF__", nginx_conf),
            project_name,
        )
    _write(root / "backend" / "Dockerfile", BACKEND_DOCKERFILE, project_name)

    if local:
        _write(root / "prod", PROD_SCRIPT, project_name, executable=True)
        _write(root / "docker-compose.prod.yml", PROD_COMPOSE, project_name)
        _write(root / ".env.prod.example", ENV_PROD_EXAMPLE, project_name)

    _update_gitignore(root, project_name)


def ensure_lockfiles(root: Path, flavor: str = "react"):
    """Best-effort lockfile bootstrap so CI's frozen installs work on day one.

    CI runs `uv sync --frozen` and `npm ci`, both of which require committed
    lockfiles a fresh generator run does not have. Resolution-only commands
    (`uv lock`, `npm install --package-lock-only`) avoid installing full
    dependency trees during generation; failure is non-fatal — the user just
    commits locks after their first manual sync/install instead.
    """
    import subprocess

    backend = root / "backend"
    if subprocess.run(["uv", "lock"], cwd=backend, capture_output=True).returncode == 0:
        print("[OK] Created: backend/uv.lock")
    else:
        print(
            "[WARN] Could not create backend/uv.lock (uv missing or offline?). "
            "Run `uv lock` in backend/ before pushing."
        )

    if flavor == "react":
        frontend = root / "frontend"
        result = subprocess.run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts"],
            cwd=frontend,
            capture_output=True,
        )
        if result.returncode == 0:
            print("[OK] Created: frontend/package-lock.json")
        else:
            print(
                "[WARN] Could not create frontend/package-lock.json (npm missing or offline?). "
                "Run `npm install` in frontend/ before pushing."
            )


def _update_gitignore(root: Path, project_name: str):
    """Real secrets and generated certs must never be committed."""
    gitignore = root / ".gitignore"
    additions = [
        ".env.prod",
        "frontend/certs/",
        "backups/",
        f".{project_name.replace('-', '_')}.pids",
    ]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing = [entry for entry in additions if entry not in existing.split()]
    if missing:
        with gitignore.open("a", encoding="utf-8") as handle:
            handle.write("\n# Devops scaffolding (./dev, ./prod)\n")
            handle.write("\n".join(missing) + "\n")
        print(f"[OK] Updated: {gitignore}")
