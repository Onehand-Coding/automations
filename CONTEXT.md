# Automations CLI — Context

## Project Overview

A Python CLI tool for automating development and file management tasks — project scaffolding, documentation generation, file organization, downloading (video/audio/files/torrents), gist management, subtitle tools, DB backups, and more.

## Current Status (2026-08-26)

### What's Working
- All existing features (project generation, downloads, gists, subtitles, backups, etc.)
- `generate-project --fullstack` (FastAPI + React) with Ctrl+C handling
- `generate-project --flutter` (FastAPI + Flutter frontend)
- `--local` on both flavors (LAN prod stack); dev/prod parity checked by `~/Coding/projects/standards/scripts/check-deploy-parity.sh`
- Ctrl+C clean exit (exit code 130) across all scripts
- CI (`.github/workflows/ci.yml`) runs ruff check, ruff format check, and `pytest` on push/PR

### What's Broken / Needs Work
- passlib bcrypt warning (`trapped error reading bcrypt version`) — harmless, but uses fallback backend
- Flutter frontend requires web support (run `flutter create .` in frontend/)

### Flavor Options
- `--fullstack` / `-f`: FastAPI backend + React (Vite + TypeScript + Tailwind + shadcn/ui) + optional Docker Compose
- `--flutter` / `-F`: FastAPI backend (async SQLAlchemy + asyncpg, JWT auth, auto-seeded demo user) + Flutter frontend (Riverpod + GoRouter + Dio + flutter_secure_storage)
- `--compose` / `-c`: adds docker-compose.yml with PostgreSQL, switches backend to asyncpg
- `--local` / both flavors: adds `./prod` + docker-compose.prod.yml + TLS nginx conf for office-LAN deploys (implies --compose)

### Devops Layer (2026-08-26 rework)
- Every generated project now gets: `./dev` (replaces start.sh), `.github/workflows/ci.yml`, image Dockerfiles, plain `nginx.conf`; `./prod` stack only with `--local`
- Node pinned via ONE constant: `src/automations_cli/versions.py` (`NODE_MAJOR = "24"`) feeds engines `">=24 <25"`, Dockerfile `node:24-alpine`, and CI `node-version`. Bump = one edit. `FLUTTER_BUILD_IMAGE` there is pinned to `cirruslabs/flutter:3.44.0` (newest tag the registry publishes — it lags Flutter stable; verify before bumping)
- CI is seniorhub-shaped plus pwdims' image-scan job: security job owns pip-audit + npm audit (via emitted `frontend/scripts/check-audit.cjs`, empty allow-list), pytest, tsc/lint/vitest/build, trivy CRITICAL-blocking/HIGH-report scans of built images with GHA cache scopes shared with publish, ghcr publish on main gated on image-scan. Image names derive from project name under the `onehand-coding` org
- Day-one green: sample health pytest (backend `[dependency-groups] dev`, NOT optional-deps — plain `uv sync` must install it) + App.test.tsx with vitest; `ensure_lockfiles()` bootstraps uv.lock/package-lock.json so CI's frozen installs work
- `./dev` DB block is conditional on docker-compose.yml existing; runs `uv run db-upgrade` only if `backend/alembic.ini` exists; migration failure aborts startup
- `./prod up` enforces chmod 600 .env.prod + mkdir/chown ./backups per docs/local-deploy-standard.md

### Key Decisions
- Short flags: `-f` = fullstack, `-F` = flutter, `-c` = compose
- Sublime venv param: `backend_in_subdir=True` (generic, covers both flavors)
- Flutter arch: feature-first (Riverpod providers, GoRouter shell routes, Dio API client)
- Demo user auto-seeded via FastAPI lifespan: `demo@example.com` / `demo1234`
- All scripts exit 130 on Ctrl+C
- Node major pinned (not floating "latest"): reproducible builds across dev/CI/prod; breaking majors ship every ~6 months
- Backend dev deps use PEP 735 `[dependency-groups]` to match pwdims/seniorhub (extras would break CI's plain `uv sync --frozen`)
- Generated projects start with empty npm-audit allow-list; entries require written rationale in check-audit.cjs
- CI gates on ruff check, ruff format check, and pytest across `src/` and `tests/`; `B008` and `E501` are ignored (Typer defaults and unwrappable strings)

### Relevant Files
- `src/automations_cli/main.py` — Typer CLI entry
- `src/automations_cli/project_generator.py` — argparse + dispatch
- `src/automations_cli/flutter.py` — Flutter + FastAPI generator
- `src/automations_cli/fullstack.py` — reference for flavor pattern
- `src/automations_cli/local_deploy.py` — dev/prod/CI/Dockerfile templates (scaffold_devops, ensure_lockfiles)
- `src/automations_cli/versions.py` — NODE_MAJOR / NODE_ENGINES / FLUTTER_BUILD_IMAGE single source of truth

### Recent Work
- Reworked generator devops layer: dev/prod default, Node 24 constant, CI workflow emission, vitest+pytest day-one tests, vite ^6, eslint config fix (lint was silently broken before), flutter flavor parity
- Pinned FLUTTER_BUILD_IMAGE to cirruslabs/flutter:3.44.0 (registry-verified) and added pwdims-style trivy image-scan gating ghcr publish to both CI templates
- Verified end-to-end: bash -n, uv sync --frozen + pytest (both flavors), npm ci/lint/test/build, compose config, standards-repo parity checker (only expected sidecar gaps), CI YAML parse with image-scan→cd chain

### Takeout Gotchas
- Requires `exiftool` on PATH (Fedora: `dnf install perl-Image-ExifTool`)
- New-format takeouts use `<name>.supplemental-metadata.json` — matched via the general suffix fallback in `find_matching_json`
- Duplicate-pair naming bug: for `x.jpg` + `x(1).jpg` pairs, pattern 5 matches the original to the `(1)` JSON (`(` sorts before `.`) and the `(1)` file matches nothing — fix manually after running (dates are identical)
- Files Google uploads with wrong extension (PNG content as `.jpg`) fail exiftool — rename to the real extension and re-embed

## Next Steps
- (none outstanding)
