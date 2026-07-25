# Deploying API v1 to the home server (hp-server)

Runbook for getting `/api/v1` (the iOS app's backend) onto `hp-server`, alongside
the existing website. Written to be executed **by hand over SSH**, with stop
points where you paste output back before anything mutates data.

**Why by hand:** Claude's shell can reach the internet and the router but not LAN
peer hosts, so it cannot SSH to `192.168.1.251` itself. Your terminal can.

## Facts established so far

| | |
|---|---|
| Host | `hp-server` → `192.168.1.251`, MAC `e4:a4:71:ce:55:d6` |
| Access | SSH key installed for `steve@hp-server` (`ssh-copy-id` done) |
| Listening | `22` (ssh), `5000` (the wishlist app) |
| Sleep | The box sleeps and ignored Wake-on-LAN — see [Keeping it awake](#keeping-it-awake) |

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
APNS_KEY_ID=<10-char key id>
APNS_TEAM_ID=<10-char team id>
APNS_KEY_P8=<contents of AuthKey_XXXX.p8>
APNS_BUNDLE_ID=com.reitz.wishlist
APNS_USE_SANDBOX=true
```

Get the `.p8` from the Apple Developer portal (Keys → new key → APNs). Delivery
runs through the existing Celery worker, so that must be running for pushes to
send.

## Keeping it awake

The box slept through five Wake-on-LAN packets, so WoL is likely disabled in
BIOS. For a server the family relies on:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

Also give it a **static DHCP reservation** on the router — `hp-server` only
resolves via the router's wildcard domain today, so its address can move, which
already sent one debugging session down a blind alley.
