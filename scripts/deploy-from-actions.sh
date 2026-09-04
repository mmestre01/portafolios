#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
PRODUCTION_DIR="/home/mmestre01/Desktop/portafolios"
DEPLOY_STATE="$PRODUCTION_DIR/.deploy-commit"
CURRENT_SHA="${GITHUB_SHA:?GITHUB_SHA is required}"
PREVIOUS_SHA=""

if [[ -f "$DEPLOY_STATE" ]]; then
  PREVIOUS_SHA="$(<"$DEPLOY_STATE")"
fi

changed() {
  if [[ -z "$PREVIOUS_SHA" ]] || ! git -C "$SOURCE_DIR" cat-file -e "$PREVIOUS_SHA^{commit}" 2>/dev/null; then
    return 0
  fi
  ! git -C "$SOURCE_DIR" diff --quiet "$PREVIOUS_SHA" "$CURRENT_SHA" -- "$@"
}

echo "Deploying $CURRENT_SHA (previous: ${PREVIOUS_SHA:-none})"

# Build in the runner workspace. Production is not touched if a build fails.
if changed gitweb/gitweb-frontend; then
  npm --prefix "$SOURCE_DIR/gitweb/gitweb-frontend" ci
  npm --prefix "$SOURCE_DIR/gitweb/gitweb-frontend" run build
fi

if changed felices26Gema; then
  npm --prefix "$SOURCE_DIR/felices26Gema" ci
  npm --prefix "$SOURCE_DIR/felices26Gema" run build
fi

# Update Python dependencies only when their manifests change.
if [[ -n "$PREVIOUS_SHA" ]] && changed requirements.txt; then
  "$PRODUCTION_DIR/venv/bin/python" -m pip install -r "$SOURCE_DIR/requirements.txt"
fi
if [[ -n "$PREVIOUS_SHA" ]] && changed gitweb/requirements.txt; then
  "$PRODUCTION_DIR/venv/bin/python" -m pip install -r "$SOURCE_DIR/gitweb/requirements.txt"
fi
if [[ -n "$PREVIOUS_SHA" ]] && changed apirift/requirements.txt; then
  "$PRODUCTION_DIR/venv/bin/python" -m pip install -r "$SOURCE_DIR/apirift/requirements.txt"
fi
if [[ -n "$PREVIOUS_SHA" ]] && changed BuscaGas/requirements.txt; then
  "$PRODUCTION_DIR/BuscaGas/.venv/bin/python" -m pip install -r "$SOURCE_DIR/BuscaGas/requirements.txt"
fi

# Root application and static content. Never copy local secrets or state.
for file in app.py config.py index.html cv.pdf favicon.svg requirements.txt README.md; do
  [[ -f "$SOURCE_DIR/$file" ]] && install -m 0644 "$SOURCE_DIR/$file" "$PRODUCTION_DIR/$file"
done

sync_tree() {
  local relative="$1"
  [[ -d "$SOURCE_DIR/$relative" ]] || return 0
  mkdir -p "$PRODUCTION_DIR/$relative"
  rsync -a --delete \
    --exclude='.env' --exclude='*.db' --exclude='*.sqlite*' \
    --exclude='venv/' --exclude='.venv/' --exclude='node_modules/' \
    --exclude='build/' --exclude='dist/' \
    --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='.ruff_cache/' \
    --exclude='*.log' --exclude='uploads/' --exclude='downloads/' \
    "$SOURCE_DIR/$relative/" "$PRODUCTION_DIR/$relative/"
}

sync_tree templates
sync_tree static
sync_tree gitweb
sync_tree apirift
sync_tree BuscaGas
sync_tree raspberry-digame-client
sync_tree felices26Gema

if changed gitweb/gitweb-frontend; then
  rsync -a --delete "$SOURCE_DIR/gitweb/gitweb-frontend/build/" \
    "$PRODUCTION_DIR/gitweb/gitweb-frontend/build/"
fi
if changed felices26Gema; then
  rsync -a --delete "$SOURCE_DIR/felices26Gema/dist/" \
    "$PRODUCTION_DIR/felices26Gema/dist/"
fi

# Restart only services whose runtime code changed.
if changed gitweb ':!gitweb/gitweb-frontend'; then sudo systemctl restart gitweb.service; fi
if changed apirift; then sudo systemctl restart apirift.service; fi
if changed app.py config.py templates static requirements.txt; then sudo systemctl restart digame.service; fi
if changed raspberry-digame-client; then sudo systemctl restart digame-client.service; fi
if changed BuscaGas; then sudo systemctl restart buscagas.service; fi

sudo nginx -t
sudo systemctl reload nginx.service

printf '%s\n' "$CURRENT_SHA" > "$DEPLOY_STATE"

for service in nginx.service gitweb.service apirift.service digame.service digame-client.service buscagas.service; do
  sudo systemctl is-active --quiet "$service"
done

curl --fail --silent --show-error --max-time 10 http://127.0.0.1/ >/dev/null
echo "Deployment completed successfully."
