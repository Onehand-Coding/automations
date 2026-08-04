"""Local-deployment (LAN) devops scaffolding for generated fullstack projects.

Emits the `dev` / `prod` script pair used by the MSWD projects (resident-hub,
pwdims, aics-tracking-system) plus the prod compose stack they drive.

This is for apps deployed on a LAN box that staff reach by IP — hence the
self-signed certificate issued for the host's LAN IP. A public/VPS deployment
needs real certificates (Caddy or nginx + Let's Encrypt against a domain), so
`prod tls` and `prod deploy` here do NOT transfer to that case.

Templates are plain strings with __TOKEN__ placeholders rather than f-strings:
shell and YAML are dense with braces, and doubling every one of them is a
reliable source of bugs.
"""

import stat
from pathlib import Path


def _write(path: Path, content: str, project_name: str, executable: bool = False):
    package_name = project_name.replace("-", "_")
    rendered = (
        content.replace("__PROJECT__", project_name)
        .replace("__PACKAGE__", package_name)
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
        pkill -15 -f 'vite.*frontend' 2>/dev/null

        sleep 1
        echo "Cleanup complete"
        echo ""

        echo "Starting PostgreSQL..."
        cd "$ROOT_DIR"
        docker compose up -d
        echo "DB ready"
        echo ""

        cleanup() {
            echo ""
            echo "Shutting down..."
            graceful_kill "$BACKEND_PID" "backend"
            graceful_kill "$FRONTEND_PID" "frontend"
            # Backstop: catches anything that escaped its process group.
            pkill -15 -f 'uvicorn.*__PACKAGE__' 2>/dev/null
            pkill -15 -f 'vite.*frontend' 2>/dev/null
            cd "$ROOT_DIR" && docker compose down
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
        npm run dev &
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
        echo "  (none)      Start everything — DB (Docker), backend, frontend"
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
        BACKUP_DIR="$REPO_DIR/backups"
        TIMESTAMP=$(date +%F_%H%M%S)
        RETENTION_DAYS=30
        mkdir -p "$BACKUP_DIR"

        DB_FILE="$BACKUP_DIR/__PACKAGE__-manual-${TIMESTAMP}.sql.gz"
        $COMPOSE up -d --wait db
        $COMPOSE exec -T db pg_dump -U postgres __PACKAGE__ | gzip > "$DB_FILE"
        echo "Database backup: $DB_FILE ($(du -h "$DB_FILE" | cut -f1))"

        find "$BACKUP_DIR" -name '__PACKAGE__-manual-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete
        echo "Backup complete."
        ;;
    restore)
        BACKUP_DIR="$REPO_DIR/backups"
        if [ -n "${2:-}" ]; then
            BACKUP_FILE="$2"
        else
            BACKUP_FILE=$(ls -t "$BACKUP_DIR"/__PACKAGE__-manual-*.sql.gz 2>/dev/null | head -1)
        fi

        if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
            echo "No backup found. Run './prod backup' first, or pass a path."
            exit 1
        fi

        echo "This OVERWRITES the production database from $BACKUP_FILE."
        read -r -p "Type the project name to confirm: " confirm
        [ "$confirm" = "__PROJECT__" ] || { echo "Aborted."; exit 1; }

        $COMPOSE up -d --wait db
        $COMPOSE exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS __PACKAGE__;"
        $COMPOSE exec -T db psql -U postgres -d postgres -c "CREATE DATABASE __PACKAGE__ OWNER postgres;"
        gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T db psql -U postgres -d __PACKAGE__
        echo "Restore complete."
        ;;
    offsite-sync)
        BACKUP_DIR="$REPO_DIR/backups"
        set -a && . "$REPO_DIR/.env.prod" && set +a
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
FROM node:24-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-tls.conf /etc/nginx/conf.d/default.conf
EXPOSE 80 443
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


def scaffold_local(root: Path, project_name: str):
    """Emit the LAN-deployment dev/prod scripts and their supporting stack.

    Replaces start.sh: `./dev` with no arguments does what start.sh did, and
    the subcommands cover the database and backup lifecycle around it.
    """
    _write(root / "dev", DEV_SCRIPT, project_name, executable=True)
    _write(root / "prod", PROD_SCRIPT, project_name, executable=True)
    _write(root / "docker-compose.prod.yml", PROD_COMPOSE, project_name)
    _write(root / ".env.prod.example", ENV_PROD_EXAMPLE, project_name)
    _write(root / "backend" / "Dockerfile", BACKEND_DOCKERFILE, project_name)
    _write(root / "frontend" / "Dockerfile", FRONTEND_DOCKERFILE, project_name)
    _write(root / "frontend" / "nginx-tls.conf", NGINX_TLS_CONF, project_name)

    # Real secrets and generated certs must never be committed.
    gitignore = root / ".gitignore"
    additions = [".env.prod", "frontend/certs/", "backups/", f".{project_name.replace('-', '_')}.pids"]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing = [entry for entry in additions if entry not in existing.split()]
    if missing:
        with gitignore.open("a", encoding="utf-8") as handle:
            handle.write("\n# Local-deployment devops (./dev, ./prod)\n")
            handle.write("\n".join(missing) + "\n")
        print(f"[OK] Updated: {gitignore}")
