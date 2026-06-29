# Automations CLI — Context

## Project Overview

A Python CLI tool for automating development and file management tasks — project scaffolding, documentation generation, file organization, downloading (video/audio/files/torrents), gist management, subtitle tools, DB backups, and more.

## Current Status (2026-06-29)

### What's Working
- All existing features (project generation, downloads, gists, subtitles, backups, etc.)
- `generate-project --fullstack` (FastAPI + React) with Ctrl+C handling
- `generate-project --flutter` (FastAPI + Flutter frontend)
- Ctrl+C clean exit (exit code 130) across all scripts

### What's Broken / Needs Work
- passlib bcrypt warning (`trapped error reading bcrypt version`) — harmless, but uses fallback backend
- Flutter frontend requires web support (run `flutter create .` in frontend/)

### Flavor Options
- `--fullstack` / `-f`: FastAPI backend + React (Vite + TypeScript + Tailwind + shadcn/ui) + optional Docker Compose
- `--flutter` / `-F`: FastAPI backend (async SQLAlchemy + asyncpg, JWT auth, auto-seeded demo user) + Flutter frontend (Riverpod + GoRouter + Dio + flutter_secure_storage)
- `--compose` / `-c`: adds docker-compose.yml with PostgreSQL, switches backend to asyncpg

### Key Decisions
- Short flags: `-f` = fullstack, `-F` = flutter, `-c` = compose
- Sublime venv param: `backend_in_subdir=True` (generic, covers both flavors)
- Flutter arch: feature-first (Riverpod providers, GoRouter shell routes, Dio API client)
- Demo user auto-seeded via FastAPI lifespan: `demo@example.com` / `demo1234`
- All scripts exit 130 on Ctrl+C

### Relevant Files
- `src/automations_cli/main.py` — Typer CLI entry
- `src/automations_cli/project_generator.py` — argparse + dispatch
- `src/automations_cli/flutter.py` — Flutter + FastAPI generator
- `src/automations_cli/fullstack.py` — reference for flavor pattern

### Recent Work
- Fixed `passlib` + `bcrypt>=5.0.0` incompatibility — pinned `bcrypt<5.0.0` in flutter pyproject.toml template
- End-to-end verified: Flutter analyze (0 errors, 0 warnings), backend starts, demo user seeds, login works

## Next Steps
- (none outstanding)
