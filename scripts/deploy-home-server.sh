#!/usr/bin/env bash
# Deploy Wishlist to hp-server (sandbox, gifts.stevereitz.dev).
#
# Automates the runbook (docs/DEPLOY_HOME_SERVER.md) + skill stop-points:
#   git pull --ff-only  →  backup  →  revision assert  →  rebuild all images
#   →  restart  →  smoke verify
# Runs FROM YOUR TERMINAL (this Mac can reach the LAN; CI runners cannot).
# Usage: ./scripts/deploy-home-server.sh [--skip-backup]
set -euo pipefail

SKIP_BACKUP=0
for arg in "$@"; do
  case "$arg" in
    --skip-backup) SKIP_BACKUP=1 ;;
    *) echo "!! unknown arg: $arg"; exit 1 ;;
  esac
done

HOST="steve@hp-server"                 # 192.168.1.251
APP_DIR="~/home-server/flask-app"      # code is baked into images (not bind-mounted)
COMPOSE_DIR="~/home-server"

# ---- 0. Preflight -----------------------------------------------------------
echo "== preflight: ssh reachable =="
ssh "$HOST" "echo ok" >/dev/null

# ---- 1. Pull the released branch -------------------------------------------
echo "== git pull --ff-only origin main =="
ssh "$HOST" "cd $APP_DIR && git status --porcelain | grep . && { echo '!! dirty worktree — stop'; exit 1; } || true"
ssh "$HOST" "cd $APP_DIR && git fetch origin && git checkout main && git pull --ff-only origin main"

# ---- 2. Back up the database -----------------------------------------------
if [[ "$SKIP_BACKUP" == "1" ]]; then
  echo "== skipping backup (--skip-backup) =="
else
  STAMP="$(date +%F-%H%M)"
  echo "== pg_dump backup → ~/wishlist-backup-${STAMP}.sql =="
  # pg container + creds live in the home-server compose project's .env
  ssh "$HOST" "cd $COMPOSE_DIR && set -a && source .env && set +a && \
    docker exec \$(docker compose ps -q postgres_db) pg_dump -U \"\$POSTGRES_USER\" \"\$POSTGRES_DB\" \
    > ~/wishlist-backup-${STAMP}.sql"
  ssh "$HOST" "test -s ~/wishlist-backup-${STAMP}.sql && echo 'backup ok' || { echo '!! empty backup — stop'; exit 1; }"
fi

# ---- 3. Record the pre-deploy revision for diagnostics ----------------------
# Procfile release phase is disabled (# migration mismatch): the live DB may sit
# at a different revision than this repo. Capture current+heads for the log;
# the real assert happens when the FRESH image runs `flask db upgrade` below
# (it fails loudly on drift/multiple heads). Running it against the OLD running
# container would be meaningless — migrations/ is baked into the image.
echo "== pre-deploy alembic revisions (diagnostic) =="
ssh "$HOST" "cd $APP_DIR && export FLASK_APP=app.py && \
  docker compose exec -T flask_app flask db current 2>&1 | tail -1" || true
ssh "$HOST" "cd $APP_DIR && export FLASK_APP=app.py && \
  docker compose exec -T flask_app flask db heads 2>&1 | tail -1" || true

# ---- 4. Pause watchtower during the swap -----------------------------------
echo "== pausing watchtower (it may auto-restart containers) =="
ssh "$HOST" "cd $COMPOSE_DIR && docker compose stop watchtower || true"

# ---- 5. Rebuild ALL three service images -----------------------------------
# Each build: service has its OWN image; building only flask_app leaves the
# worker/beat on stale code.
echo "== docker compose build flask_app celery_worker beat =="
ssh "$HOST" "cd $COMPOSE_DIR && docker compose build flask_app celery_worker beat"

# ---- 6. Migrate on the FRESH image, then restart ---------------------------
# The new migration files exist only in the rebuilt image; run upgrade against
# it via `compose run --rm` BEFORE starting containers so the schema is ready
# when the web app comes up. Fails loudly on revision drift.
echo "== flask db upgrade (fresh image; fails loudly on drift) =="
ssh "$HOST" "cd $COMPOSE_DIR && set -a && source .env && set +a && \
  docker compose run --rm -T flask_app flask db upgrade"

echo "== compose up -d --no-deps --force-recreate =="
ssh "$HOST" "cd $COMPOSE_DIR && set -a && source .env && set +a && \
  docker compose up -d --no-deps --force-recreate flask_app celery_worker beat"

# ---- 7. Resume watchtower ---------------------------------------------------
echo "== resuming watchtower =="
ssh "$HOST" "cd $COMPOSE_DIR && docker compose start watchtower || true"

# ---- 8. Smoke verify --------------------------------------------------------
echo "== smoke: /login returns 200; worker pings =="
ssh "$HOST" "curl -s -o /dev/null -w 'login:%{http_code}\n' http://localhost:5000/login"
ssh "$HOST" "docker exec celery_worker celery -A celery_app inspect ping || echo 'worker ping failed'"

echo "== API + surprise-protection smoke (paste output back) =="
ssh "$HOST" "bash -s" <<'REMOTE'
  CODE=$(curl -s -o /tmp/login.json -w '%{http_code}' \
    -X POST http://localhost:5000/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"sthreitz@gmail.com","family_code":"wishlist2025"}')
  echo "login: $CODE"
  TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/login.json'))['token'])" 2>/dev/null || true)
  [ -n "$TOKEN" ] && curl -s http://localhost:5000/api/v1/items -H "Authorization: Bearer $TOKEN" | head -c 300 || echo "no token"
  echo
REMOTE

echo "== done. If any smoke step failed, check ~/home-server/wishlist-watch.log =="
