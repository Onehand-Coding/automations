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

## Known remaining divergences

- `aics-tracking-system` splits config across `.env.prod` and
  `backend/.env.prod`; the other two use one file. The backup sidecar no
  longer reads the backend file, but the backend still does.
- `aics-tracking-system` has no Redis, worker, or RS256 JWT keys; those
  rules apply only where the service exists.
- `pwdims` gates `backend`/`frontend` behind `needs: security`, so a red
  security job skips them entirely rather than running them; the other two
  do not gate. While security was red this hid a known-failing
  forced-password-change test. Not yet reconciled.
- `pip-audit` still runs twice in `pwdims` and `aics` (`uvx pip-audit
  --local` in `backend`, `uv pip install pip-audit && pip-audit
  --skip-editable` in `security`) where `resident-hub` runs it once. Same
  duplicate-gate shape the npm rule above fixes, not yet applied to Python.
- The checker reports `n/a`, not `GAP`, when a file is missing entirely, so
  a rule cannot catch a repo that simply lacks the file. Fine for genuinely
  optional files, a hole for required ones.
