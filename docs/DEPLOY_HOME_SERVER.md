# Deploying API v1 to the home server (hp-server)

Runbook for getting `/api/v1` (the iOS app's backend) onto `hp-server`, alongside
the existing website. Written to be executed **by hand over SSH**, with stop
points where you paste output back before anything mutates data.

**Why by hand:** Claude's shell can reach the internet and the router but not LAN
peer hosts, so it cannot SSH to `192.168.1.251` itself. Your terminal can.

## Facts established so far

| | |
|---|---|
| Host | `hp-server` → `192.168.1.251`, **Ubuntu 26.04 LTS**, Linux 7.0.0-28 |
| Access | SSH key installed for `steve@hp-server` (`ssh-copy-id` done) |
| Sleep | The box sleeps and ignored Wake-on-LAN — see [Keeping it awake](#keeping-it-awake) |

### Actual topology (from Phase 0)

Docker Compose, **not** systemd, and **not** this repo's `docker-compose.yml` —
it's a separate compose project in `~/home-server`:

| Container | Image | Ports |
|---|---|---|
| `flask_app` | `home-server-flask_app` (locally built) | `0.0.0.0:5000→5000` |
| `postgres_db` | `postgres:15-alpine` | `5432` (internal) |
| `cloudflared` | `cloudflare/cloudflared` | — (public ingress) |
| `vaultwarden` | `vaultwarden/server` | `0.0.0.0:8080→80` |
| `watchtower` | `containrrr/watchtower` | — (auto-updates containers) |

Four consequences that change this deploy:

1. **Postgres, not SQLite** → back up with `pg_dump`, and migrations run inside
   the container. Note it's Postgres **15**, while this repo's own compose file
   pins 16 — don't "helpfully" align them; upgrading a live cluster is a
   separate, riskier job.
2. **No Redis and no Celery worker.** APNs push fan-out enqueues to Celery, so
   **push cannot deliver** as configured. This is safe rather than broken:
   `create_notification` commits the notification row *before* enqueuing and
   swallows enqueue failures, so in-app notifications work and only push is
   inert. Adding push means adding a redis service + a celery worker.
3. **`cloudflared` means the app is publicly reachable**, so `/api/v1` will be
   too. The only gate is the family code, and `POST /api/v1/auth/login` is rate
   limited to 5/min — but Flask-Limiter without Redis falls back to per-process
   in-memory storage, so that limit is weaker than it looks. See
   [Public exposure](#public-exposure).
4. **watchtower may restart containers on its own.** If it auto-pulls
   `home-server-flask_app`, an unexpected restart mid-deploy is possible;
   consider pausing it during the migration.

### Still unknown (Phase 0.5 answers these)

- Where the wishlist source lives, and whether it's **bind-mounted** into
  `flask_app` (a `git pull` on the host is enough) or **baked into the image**
  (requires `docker compose build`).
- The container's `DATABASE_URL` / `FAMILY_PASSWORD` / `REDIS_URL` wiring.
- The live Alembic revision.

## What this deploy changes

1. Adds the `api_v1` blueprint (token-authenticated JSON API) — additive, no web routes change.
2. **Creates two tables** via migration `e20431cbf8bc`: `api_token`, `device`.
3. Adds Python deps: `httpx[http2]`, `pyjwt[crypto]`.
4. Optionally sets `APNS_*` env vars for push (the API works fine without them).

Step 2 is the only irreversible part. Phase 2 backs the database up first.

---

## Phase 0 — Discovery (read-only, safe)

The repo ships both a `Procfile` (gunicorn) and a `docker-compose.yml`
(postgres + redis + web), so how *this* box runs the app determines everything
below. Run this and paste the whole output back:

```bash
ssh steve@hp-server bash -s <<'EOF'
echo "── host ──"; hostname; uname -sr; (lsb_release -ds 2>/dev/null || head -1 /etc/os-release)
echo "── what is serving :5000 ──"; (sudo ss -ltnp 2>/dev/null || ss -ltnp) | grep -E ':5000|:8000' || echo "nothing on 5000/8000"
echo "── docker ──"; (docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null || echo "no docker access")
echo "── systemd units mentioning wishlist/gunicorn ──"
systemctl list-units --type=service --no-pager 2>/dev/null | grep -iE 'wishlist|gunicorn|celery' || echo "none"
echo "── candidate app dirs ──"
for d in ~/wishlist ~/flask-wishlist-site /srv/wishlist /opt/wishlist /var/www/wishlist; do [ -d "$d" ] && echo "FOUND $d"; done
find ~ -maxdepth 3 -name 'app.py' -path '*wishlist*' 2>/dev/null | head
echo "── nginx/caddy in front? ──"; ls /etc/nginx/sites-enabled 2>/dev/null; ls /etc/caddy 2>/dev/null
EOF
```

**Stop here.** The output decides: Docker Compose vs systemd+gunicorn, the app
path, and whether a reverse proxy fronts it.

---

## Phase 1 — Get the API v1 code onto the server

API v1 currently lives on branch `worktree-api-v1` (PR #42). Two options:

**Preferred — merge first, deploy `main`:** merge PR #42 on GitHub, then the
server just pulls `main`. Keeps the box on a released branch.

**Or deploy the branch directly** (fine for a home server, but the box is then
on an unmerged branch — remember it):

```bash
ssh steve@hp-server
cd <APP_DIR_FROM_PHASE_0>
git remote -v                 # confirm it points at ssk42/flask-wishlist-site
git fetch origin
git status --porcelain        # MUST be empty; local edits would be clobbered below
```

If `git status` shows local changes, stop and inspect them — someone edited the
server copy directly, and that work is not in git.

```bash
git checkout main && git pull --ff-only origin main
#   ...or, for the unmerged branch:
# git fetch origin worktree-api-v1 && git checkout worktree-api-v1 && git pull --ff-only
```

---

## Phase 2 — Back up the database (do not skip)

**SQLite** (if Phase 0 showed no postgres container):

```bash
cd <APP_DIR>
cp instance/wishlist.sqlite ~/wishlist-backup-$(date +%F-%H%M).sqlite
ls -la ~/wishlist-backup-*.sqlite
```

**Postgres in Docker** (if Phase 0 showed a `postgres` container):

```bash
docker exec <PG_CONTAINER> pg_dump -U <PGUSER> <PGDATABASE> \
  > ~/wishlist-backup-$(date +%F-%H%M).sql
ls -la ~/wishlist-backup-*.sql
```

Confirm the backup file is non-empty before continuing.

---

## Phase 3 — Migration safety check (paste output back)

⚠️ The `Procfile` has its release phase commented out with
`# migration mismatch`, which means migrations have **not** been running
automatically and the live database may sit at a different Alembic revision than
this repo expects. Check before upgrading:

```bash
cd <APP_DIR>
export FLASK_APP=app.py
# match how the app is normally invoked — venv, or `docker compose exec web`
.venv/bin/flask db current    # where the live DB thinks it is
.venv/bin/flask db heads      # where the repo's migration chain ends
.venv/bin/flask db history | head -20
```

Expected healthy case: `current` is `4a8b3c9d1e2f` and `heads` is
`e20431cbf8bc` (the new api_token/device migration), i.e. exactly one step
behind.

**Stop and paste this back if:** `current` is empty, reports multiple heads, or
names a revision not in `history`. Forcing `db upgrade` through a mismatch is
how you corrupt a schema — don't.

---

## Phase 4 — Dependencies

**systemd/venv:**

```bash
cd <APP_DIR>
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import httpx, jwt; print('deps ok')"
```

**Docker:** rebuild so the image picks up the new requirements:

```bash
cd <APP_DIR>
docker compose build web-prod   # or `web`, per Phase 0
```

Note: `pyjwt[crypto]` pulls in `cryptography`. On this Mac that needed a pinned
version (no wheel for the local Python), but Linux has wheels, so a plain
install should be fine. If it tries to compile from source, install
`build-essential libssl-dev libffi-dev python3-dev` first.

---

## Phase 5 — Run the migration

Only after Phase 2 (backup) and Phase 3 (clean revision check):

```bash
cd <APP_DIR>
export FLASK_APP=app.py
.venv/bin/flask db upgrade          # docker: docker compose exec web flask db upgrade
.venv/bin/flask db current          # should now report e20431cbf8bc
```

Verify the tables exist:

```bash
# SQLite
sqlite3 instance/wishlist.sqlite ".tables" | tr ' ' '\n' | grep -E 'api_token|device'
# Postgres
docker exec <PG_CONTAINER> psql -U <PGUSER> -d <PGDATABASE> -c '\dt' | grep -E 'api_token|device'
```

---

## Phase 6 — Restart and verify

```bash
# systemd
sudo systemctl restart <WISHLIST_UNIT>   # name from Phase 0
sudo systemctl status  <WISHLIST_UNIT> --no-pager | head -15
# docker
docker compose up -d web-prod && docker compose logs --tail=30 web-prod
```

Smoke-test the API from the server itself (replace the family code if changed):

```bash
curl -s -o /tmp/login.json -w 'login: %{http_code}\n' \
  -X POST http://localhost:5000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"sthreitz@gmail.com","family_code":"wishlist2025"}'
cat /tmp/login.json
```

Expect `200` and `{"token":"…","user":{…}}`. Then confirm the token works and
**surprise protection holds** — your own items must come back with no `status`
field at all:

```bash
TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/login.json'))['token'])")
curl -s http://localhost:5000/api/v1/users -H "Authorization: Bearer $TOKEN" | head -c 300; echo
curl -s http://localhost:5000/api/v1/items -H "Authorization: Bearer $TOKEN" | head -c 400; echo
```

Also check the **website still works** (this deploy touched shared price-fetching
code): load a couple of pages and refresh a price on an item.

---

## Phase 7 — Point the iOS app at the server

`ios/WishlistKit/WishlistAPI.swift` currently hardcodes the dev URL:

```swift
public static let defaultBaseURL = URL(string: "http://localhost:8000")!
```

For a device on your LAN, that becomes `http://hp-server:5000` (or the IP).
Two caveats:

1. **Plain HTTP needs an ATS exception per domain.** The app and the extension
   currently except only `localhost`; add `hp-server`/the IP, or better, put
   HTTPS in front (Caddy gets you a local cert with almost no config) and drop
   the exceptions entirely.
2. **The Keychain token only persists on a signed build.** Unsigned simulator
   builds re-login each launch and the Share Extension can't read the token at
   all — expected, not a bug. TestFlight/device builds behave properly.

---

## Rollback

```bash
# 1. Revert the code
cd <APP_DIR> && git checkout <PREVIOUS_SHA> && sudo systemctl restart <UNIT>

# 2. Undo the migration (drops api_token + device — they hold only device
#    registrations and API tokens, so this loses nothing but forces re-login)
export FLASK_APP=app.py && .venv/bin/flask db downgrade 4a8b3c9d1e2f

# 3. Or restore wholesale from the Phase 2 backup
cp ~/wishlist-backup-<STAMP>.sqlite instance/wishlist.sqlite    # SQLite
# docker exec -i <PG> psql -U <USER> -d <DB> < ~/wishlist-backup-<STAMP>.sql
```

---

## Push notifications (optional, later)

The API is fully functional without these; push simply no-ops until all four are
set. Add to the service's environment (systemd drop-in or compose `environment:`):

```
APNS_KEY_ID=<10-char key id, e.g. the XXXX in AuthKey_XXXX.p8>
APNS_TEAM_ID=<10-char team id>
APNS_BUNDLE_ID=com.reitz.wishlist
APNS_USE_SANDBOX=true      # true for dev-signed builds, false for TestFlight
```

The signing key itself is a **file**, not an env var — a PKCS8 key is multi-line
PEM and `.env`/compose `environment:` handle that badly. Mount it and point at
it (`APNS_KEY_P8_PATH` takes precedence over inline `APNS_KEY_P8`):

```yaml
    volumes:
      - ./secrets/AuthKey_XXXXXXXXXX.p8:/run/secrets/apns.p8:ro
    environment:
      - APNS_KEY_P8_PATH=/run/secrets/apns.p8
```

All of it goes on **both** `flask_app` and `celery_worker` — the web app decides
whether push is enabled, the worker does the sending. An unreadable path logs an
error and leaves push disabled rather than failing the request that triggered it.

Get the `.p8` from the Apple Developer portal (Keys → new key → APNs). Delivery
runs through the existing Celery worker, so that must be running for pushes to
send.

## Cloudflare blocks non-browser clients (must fix for the iOS app)

Verified 2026-07-25: every request to `https://gifts.stevereitz.dev/api/v1/…`
from a non-browser client returns **HTTP 403 with Cloudflare's "Just a moment…"
managed-challenge page**, not JSON. TLS itself is healthy (valid cert, HTTP/2).

`URLSession` cannot solve a JavaScript challenge, so **the iOS app cannot use
this hostname until the API path is exempted.** In the Cloudflare dashboard:

> **Security → WAF → Custom rules → Create rule**
> - Field `URI Path`, operator `starts with`, value `/api/v1/`
> - Action: **Skip** → check *Managed Challenge* (and "All remaining custom
>   rules"), or use Configuration Rules to set Security Level → *Essentially Off*
>   for that path.

Verify from any machine — a JSON body rather than HTML means it worked:

```bash
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
  https://gifts.stevereitz.dev/api/v1/users     # want: 401 application/json
```

**Tradeoff to accept knowingly:** exempting `/api/v1/` removes Cloudflare's bot
protection from `POST /api/v1/auth/login`, leaving the family code exposed to
automated guessing. The app's own `5/min` limit is the only remaining brake —
and without Redis that limit is per-worker in memory (see below). Adding Redis
matters more once this exemption exists.

## Adding Redis + a Celery worker

Fixes two gaps at once: APNs push currently cannot deliver (no broker), and
Flask-Limiter silently falls back to per-process memory, so `5/min` is really
"5 per minute per gunicorn worker, reset on restart".

Add to `~/home-server/docker-compose.yml`:

```yaml
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: always
    volumes:
      - ./redis-data:/data

  celery_worker:
    build: ./flask-app
    container_name: celery_worker
    restart: always
    command: celery -A celery_app worker --loglevel=info
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - FAMILY_PASSWORD=${FAMILY_PASSWORD}
      - FLASK_ENV=${FLASK_ENV}
```

…and add `REDIS_URL=redis://redis:6379/0` to `flask_app`'s `environment:` too
(both processes need it — the web app to enqueue and rate-limit, the worker to
consume). Then:

```bash
cd ~/home-server && docker compose up -d redis celery_worker flask_app && docker compose logs --tail=20 celery_worker
```

The worker log should show it connecting to `redis://redis:6379/0` and listing
the registered tasks (including `tasks.send_push`). Note `celery_worker` reuses
the same `build: ./flask-app`, so it stays in lockstep with the web image.

## Public exposure

`cloudflared` fronts this box, so anything on `:5000` is reachable from the
internet — including `/api/v1`. Worth doing before or soon after this deploy:

- **Verify the rate limit actually applies.** Flask-Limiter with no Redis uses
  per-process memory, so `5/min` on login is per-worker and resets on restart.
  Adding a redis service fixes this *and* unblocks Celery/push.
- **Confirm the family code is strong.** It is the only credential for both the
  website and the API; the config default (`wishlist2025`) should not be what's
  running in production.
- **Prefer HTTPS via the tunnel** for the iOS app's base URL — a Cloudflare
  hostname gives you TLS for free, which means no ATS exceptions in the app and
  no plaintext family code on the wire.

## Keeping it awake

The box slept through five Wake-on-LAN packets, so WoL is likely disabled in
BIOS. For a server the family relies on:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

Also give it a **static DHCP reservation** on the router — `hp-server` only
resolves via the router's wildcard domain today, so its address can move, which
already sent one debugging session down a blind alley.
