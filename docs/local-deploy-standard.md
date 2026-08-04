# LAN-deployment devops standard

The shape shared by the MSWD office-LAN apps — `resident-hub`, `pwdims`,
`aics-tracking-system` — and emitted by `project_generator --local`.

Each rule below exists because the absence of it broke something in
production. None of them are style preferences. Check a repo with:

```bash
./scripts/check-deploy-parity.sh ~/Coding/projects/{resident-hub,pwdims,aics-tracking-system}
```

The checker exits non-zero on any gap, so it can run from CI or a pre-push
hook. Add a rule there whenever a new failure mode is found — that is what
keeps this document from going stale.

## The rules

**`.env.prod` is the only env file, and it is never sourced.**
`./prod` reads single keys with `env_get()`; `docker compose` gets
`--env-file .env.prod`. Sourcing it with `set -a; . .env.prod` treats
docker-compose syntax as shell: an unquoted value with a space
(`FIRST_ADMIN_FULL_NAME=System Administrator`) runs its second word as a
command and, under `set -e`, kills the script. Any `$(...)` that lands in a
value executes. `env_get` returns both as literal text.

*Failure this prevents:* `pwdims` sourced `.env` — a file that never existed
— so the `[ -f ]` test failed silently and `./prod backup`, `restore` and
`offsite-sync` all aborted on an unset passphrase. The stale instruction
came from `.env.prod.example` saying "Copy to `.env`".

**`./prod up` creates `./backups` before compose runs**, with
`mkdir -p` + `chown "$(id -u):$(id -g)"`. If a bind-mount source does not
exist, the Docker daemon creates it as `root:root`; sidecars running as
`HOST_UID:HOST_GID` then cannot write to it.

*Failure this prevents:* both `resident-hub` backup sidecars sat `unhealthy`
for hours logging `Permission denied`, looking scheduled, while **zero
backups existed**.

**Backups are encrypted at rest and mode 600.** `umask 077` plus
`openssl enc -aes-256-cbc -pbkdf2 -salt`, keyed by
`BACKUP_ENCRYPTION_PASSPHRASE`. These dumps are the entire database in one
file, on a shared office machine, holding names, birthdates, addresses,
contact numbers, ID numbers and case narratives.

**`restore` verifies before it drops.** Decrypt and decompress to a temp
file, confirm `PostgreSQL database dump` appears in the first five lines,
*then* drop the database. A wrong passphrase must fail while the live data
is still intact — not after.

**Sidecar scripts write to a temp file, not through a pipe.** `sh` reports
only the last command's exit status, so `pg_dump | gzip | openssl` reports
success when `pg_dump` failed and the encryption merely encrypted nothing.
Dump first, check, then encrypt, and remove both files on failure.

**Sidecar prune is count-based (newest 14), not age-based.** An age-based
prune deletes every backup if the stack sat down longer than the retention
window. Manual `./prod backup` dumps may prune by age
(`BACKUP_RETENTION_DAYS`) because they are taken deliberately.

**Healthcheck globs must track the filename.** Adding `.enc` to backup
filenames without updating `find -name 'auto-*.sql.gz'` leaves the sidecars
permanently unhealthy while working perfectly.

**`openssl` is baked into the sidecar image.** `postgres:16-alpine` and
`alpine:3.20` do not ship it, and the sidecars run as a non-root
`HOST_UID` that cannot `apk add` at start.

**`CORS_ORIGINS` includes the port.** It is both the CORS config and the
CSRF allowlist, matched on exact netloc. `/auth/login` has no CSRF check
but `/auth/refresh` does, so a missing `:7443` lets people log in and then
bounces them at the first refresh — which reads as "I can't log in".

**No `env_file:` in `docker-compose.prod.yml` — name the keys under
`environment:`.** `env_file` injects the *whole* file and has no exclusion
mechanism, so every service using it holds `BACKUP_ENCRYPTION_PASSPHRASE`,
`OFFSITE_TARGET`, `GRAFANA_ADMIN_PASSWORD` and the raw DB/Redis passwords —
inside the internet-facing backend container, which reads none of them.
Encryption converts a leak risk into a loss risk, so the passphrase is the one
secret with no business being in the most exposed process on the box.

Use **list form** (`- KEY`), never map form (`KEY: ${KEY}`). In list form an
unset key resolves to null and is simply not passed to the container, which is
exactly what `env_file` did — the app's own default survives. Map form passes
an empty string instead, silently overriding that default with `""`. Verify
with `docker compose config`, not by reading the YAML.

The authoritative key list is the app's pydantic `Settings` field set: those
are the only keys it can read at all, so a list built from them takes nothing
away. Add a key when you add a `Settings` field; a key that is not a `Settings`
field does not belong there. `resident-hub` anchors the list once
(`x-app-env: &app-env`) because `backend` and `worker` must not drift apart.

*Failure this prevents:* `aics` kept a *second* env file, `backend/.env.prod`,
purely because `env_file` could not exclude the ops secrets — and `docs/DEPLOY.md`
never scp'd it to the server. Naming the keys removed the reason for the second
file, so the split is gone.

**Each dependency tree is scanned exactly once, in the `security` job.**
`pip-audit` for Python; for npm, `npm audit --json` piped into
`frontend/scripts/check-audit.cjs`, which fails on any high/critical finding
that is not on a reviewed, commented allow-list. The script is byte-identical
in all three repos — only `ALLOWED_GHSA_IDS` is meant to differ. Never add a
second `npm audit` to the frontend/build job.

*Failure this prevents:* every repo ran the scan twice under two different
policies. `aics` ran `--audit-level=high` in `security` and
`--audit-level=critical` in `frontend`, so the weaker copy called the tree
clean while the stricter one failed on the same lockfile. `pwdims` ran
`--audit-level=high` against an allow-listing gate scoped to `--omit=dev`.
Both repos therefore reported two opposite verdicts at once, and the red job
was written off as noise while it was reporting real findings.

**The npm scan covers dev dependencies.** Build tooling ships nothing to
users, but a compromised `vite` or `postcss` compromises the bundle it
produces. `--omit=dev` is the wrong scope for a build gate — and in practice
the drifted dev tooling *was* the finding.

**A red npm audit usually means stale dependencies, not an unfixable
advisory.** Compare installed versions across the three repos before reaching
for the allow-list. On 2026-08-04, `pwdims` reported six findings and `aics`
seven where `resident-hub` reported one; every difference was version drift
(`vite` 5.4.21 vs 6.4.3, `postcss` 8.5.16 vs 8.5.25, `undici` 7.28.0 vs
7.29.0, `brace-expansion`), and all of it cleared with `npm update` plus one
declared-range bump. The apps share a dependency shape, so a finding in one
and not the others is drift until proven otherwise.

**Keep `vite` inside the peer range `vitest` declares.** vitest 4 requires
`vite ^6 || ^7 || ^8`. Against a declared `vite ^5`, npm satisfies that peer
by installing a *second*, nested vite for the test runner — so the suite
validates a different transform pipeline than the one that builds the
shipped bundle, and nothing errors. `npm ls vite --all` is the only place it
shows.

## Key custody

Encryption converts a leak risk into a loss risk. An encrypted dump is
unrecoverable without its passphrase, and each of these repos now has a
distinct one in its own gitignored `.env.prod`.

Read one out with:

```bash
sed -n 's/^BACKUP_ENCRYPTION_PASSPHRASE=//p' .env.prod | head -1
```

Three passphrases living only on the machine whose disk failure they exist
to survive is not a backup strategy. They need a durable copy off that box.

**One dependency scan per tree, and it covers dev dependencies too.** This
applies to `pip-audit` exactly as it does to `npm audit`. Both live in the
`security` job, which syncs with dev deps (`uv sync --frozen`, no
`--no-dev`); no second scan anywhere else. Deleting the duplicate was not
enough on its own here — the two Python scans had *different scope*, and the
one in the `backend` job was the wider of the pair, so the surviving scan had
to drop `--no-dev` before the duplicate could go. A duplicate gate is worth
removing; silently narrowing coverage while removing it is worse than the
duplicate was.

## Known remaining divergences

- `aics-tracking-system` has no Redis, worker, or RS256 JWT keys; those
  rules apply only where the service exists.
