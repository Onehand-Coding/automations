#!/usr/bin/env bash
# Audit LAN-deployment repos against the devops standard.
#
#   ./scripts/check-deploy-parity.sh ~/Coding/projects/{resident-hub,pwdims,aics-tracking-system}
#
# Every check encodes a failure that actually happened in production, not a
# style preference. Exits non-zero if any repo has a gap, so it can run from
# CI or a pre-push hook. See docs/local-deploy-standard.md for the why.
set -uo pipefail

[ $# -ge 1 ] || { echo "usage: $0 <repo-dir> [repo-dir...]" >&2; exit 2; }

FAILURES=0
NAMES=()
for r in "$@"; do NAMES+=("$(basename "$r")"); done

# name | file (relative) | grep -E pattern | expect present(1) or absent(0)
#   | optional guard: rule only applies if this pattern is in the compose file
#
# The guard keeps the checker honest. The root-owned-bind-mount rules are
# meaningless in a project whose compose never bind-mounts ./backups, and a
# checker that reports a gap there teaches people to ignore it.
CHECKS=(
  "env_get reads .env.prod|prod|env_get\(\) \{|1"
  "no stale '. .env' sourcing|prod|^[^#]*\. \"\\\$REPO_DIR/\.env\"|0"
  "up: mkdir+chown ./backups|prod|chown \"\\\$\(id -u\):\\\$\(id -g\)\"|1|- \./backups:"
  "up: exports HOST_UID/GID|prod|export HOST_UID|1|- \./backups:"
  "backup: umask 077|prod|umask 077|1"
  "backup: encrypts at rest|prod|sql\.gz\.enc|1"
  "backup: retention from env|prod|env_get BACKUP_RETENTION_DAYS|1"
  "restore: verify before DROP|prod|Verifying backup before|1"
  "env example: passphrase key|.env.prod.example|^BACKUP_ENCRYPTION_PASSPHRASE=|1"
  "env example: says .env.prod|.env.prod.example|[Cc]opy to \.env \(|0"
  "sidecar dumps encrypted|scripts/pg_backup.sh|BACKUP_ENCRYPTION_PASSPHRASE|1"
  "sidecar umask 077|scripts/pg_backup.sh|umask 077|1"
  "sidecar healthcheck glob .enc|docker-compose.prod.yml|auto-\*\.sql\.gz' |0"
  # env_file injects the *entire* file and offers no way to exclude a key, so
  # any service using it holds BACKUP_ENCRYPTION_PASSPHRASE — the one secret
  # whose loss costs every backup — inside the internet-facing container. Name
  # the keys under `environment:` instead. Use list form (`- KEY`): an unset
  # key stays unset, matching env_file. Map form (`KEY: ${KEY}`) injects "" and
  # silently overrides the app's own default.
  "no env_file: keys are named|docker-compose.prod.yml|^[[:space:]]*env_file:|0"
  # CI dependency gate. All three repos once ran npm audit twice under two
  # different policies, so the same lockfile was reported clean by one job and
  # broken by another — and the red one got treated as noise for weeks.
  "npm gate: allow-list script|frontend/scripts/check-audit.cjs|ALLOWED_GHSA_IDS|1"
  "npm gate: wired into CI|.github/workflows/ci.yml|check-audit\.cjs|1"
  "npm gate: no blunt threshold|.github/workflows/ci.yml|npm audit --audit-level|0"
  "npm gate: dev deps in scope|.github/workflows/ci.yml|npm audit.*--omit=dev|0"
  # Same rule for the Python tree. The second copy lived in the `backend` job as
  # `uvx pip-audit --local` and was the only one syncing dev deps, so deleting
  # it as a "duplicate" would have narrowed coverage instead of unifying it —
  # the surviving scan had to widen first.
  "pip gate: wired into CI|.github/workflows/ci.yml|uv run pip-audit|1"
  "pip gate: one scan, not two|.github/workflows/ci.yml|uvx pip-audit|0"
  "pip gate: dev deps in scope|.github/workflows/ci.yml|uv sync --frozen --no-dev|0"
)

printf '%-32s' "check"
for n in "${NAMES[@]}"; do printf '%-22s' "$n"; done
echo
printf '%.0s-' $(seq $((32 + 22 * $#))); echo

for c in "${CHECKS[@]}"; do
  IFS='|' read -r label file pattern expect guard <<< "$c"
  printf '%-32s' "$label"
  for r in "$@"; do
    # Guard first, then existence. Whether a rule *applies* is the guard's job;
    # once it applies, a missing file is a gap, not an exemption. Checking
    # existence first would report a guarded-out rule as a false GAP.
    #
    # -- so a pattern starting with '-' isn't parsed as grep options; without
    # it those checks silently reported n/a on repos that do apply.
    if [ -n "${guard:-}" ] && ! grep -qE -- "$guard" "$r/docker-compose.prod.yml" 2>/dev/null; then
      printf '%-22s' "n/a"
      continue
    fi
    # A missing file used to print n/a, which meant no rule could catch a repo
    # that simply deleted the thing being audited — the strictest possible
    # gate and the total absence of one scored identically.
    if [ ! -e "$r/$file" ]; then
      printf '%-22s' "GAP (no file)"
      FAILURES=$((FAILURES + 1))
      continue
    fi
    if grep -qE -- "$pattern" "$r/$file" 2>/dev/null; then found=1; else found=0; fi
    if [ "$found" = "$expect" ]; then
      printf '%-22s' "ok"
    else
      printf '%-22s' "GAP"
      FAILURES=$((FAILURES + 1))
    fi
  done
  echo
done

echo
if [ "$FAILURES" -eq 0 ]; then
  echo "All repos match the standard."
else
  echo "$FAILURES gap(s) found — see docs/local-deploy-standard.md"
fi
exit $(( FAILURES > 0 ))
