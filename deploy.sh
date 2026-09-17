#!/usr/bin/env bash
# Apply systemd unit, then pull/build and start the proxy container.
# Does not install a host mihomo package. Does not change .env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKIP_DOCKER=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [--skip-docker]

Applies configs from the repository:

  deploy/mihomo-proxy.service  -> /etc/systemd/system/mihomo-proxy.service
  docker compose up -d --build --pull always --force-recreate

Pulls metacubex/mihomo:latest, rebuilds the local image, and recreates
the container so entrypoint re-runs envsubst (schema + .env).

Does not install mihomo on the host and does not change .env.

To update later: git pull --ff-only && ./deploy.sh

  --skip-docker   only install the systemd unit, do not touch the container
EOF
}

for arg in "$@"; do
  case "$arg" in
    --skip-docker) SKIP_DOCKER=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "error: '$1' not found" >&2
    exit 1
  }
}

env_file_value() {
  local key="$1" file="$2"
  local val=""
  if [[ -f "$file" ]]; then
    val="$(awk -v k="$key" '
      index($0, k "=") == 1 {
        print substr($0, length(k) + 2)
        exit
      }
    ' "$file")"
  fi
  val="${val%$'\r'}"
  val="${val#"${val%%[![:space:]]*}"}"
  val="${val%"${val##*[![:space:]]}"}"
  printf '%s' "$val"
}

run_sudo() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

need_cmd docker
need_cmd systemctl
if [[ "$(id -u)" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
  echo "error: need root or sudo to install the systemd unit" >&2
  exit 1
fi

if [[ ! -f "$ROOT/.env" ]]; then
  echo "==> creating .env from .env.example"
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

secret="$(env_file_value MIHOMO_API_SECRET "$ROOT/.env")"
if [[ -z "$secret" ]]; then
  echo "error: fill MIHOMO_API_SECRET in $ROOT/.env before deploy" >&2
  exit 1
fi
case "$secret" in
  change-me|CHANGE-ME|changeme|replace-me|REPLACE_ME|replace_me)
    echo "error: MIHOMO_API_SECRET is a placeholder; generate one (openssl rand -hex 32)" >&2
    exit 1
    ;;
esac

missing=0
for var in SUB1_URL SUB2_URL SUB3_URL SUB4_URL SUB5_URL; do
  val="$(env_file_value "$var" "$ROOT/.env")"
  if [[ -z "$val" ]]; then
    echo "error: required variable $var is empty or unset in $ROOT/.env" >&2
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "==> ensuring data/"
mkdir -p "$ROOT/data"

if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_commit="$(git -C "$ROOT" rev-parse --short HEAD)"
  git_title="$(git -C "$ROOT" log -1 --first-parent --no-merges --pretty=%s)"
  if [[ -z "$git_title" ]]; then
    git_title="$(git -C "$ROOT" log -1 --pretty=%s)"
  fi
else
  git_commit="unknown"
  git_title="unknown"
fi
echo "==> git commit ${git_commit} ${git_title}"

echo "==> installing mihomo-proxy.service (WorkingDirectory=$ROOT)"
docker_bin="$(command -v docker)"
unit_tmp="$(mktemp)"
awk -v wd="$ROOT" -v docker="$docker_bin" '
  /^WorkingDirectory=/ { print "WorkingDirectory=" wd; next }
  /^ExecStart=/ { print "ExecStart=" docker " compose up -d"; next }
  /^ExecStop=/ { print "ExecStop=" docker " compose stop"; next }
  { print }
' "$ROOT/deploy/mihomo-proxy.service" > "$unit_tmp"
run_sudo install -m 644 "$unit_tmp" /etc/systemd/system/mihomo-proxy.service
rm -f "$unit_tmp"

echo "==> systemd daemon-reload"
run_sudo systemctl daemon-reload
run_sudo systemctl enable mihomo-proxy.service

if [[ "$SKIP_DOCKER" -eq 1 ]]; then
  echo "==> skip docker"
else
  echo "==> docker compose up -d --build --pull always --force-recreate"
  (
    cd "$ROOT"
    docker compose up -d --build --pull always --force-recreate
  )
  run_sudo systemctl start mihomo-proxy.service
fi

echo
echo "done"
echo "  network      telegram-proxy (alias proxy)"
echo "  SOCKS        socks5h://proxy:11808"
echo "  API          http://proxy:19090"
if [[ "$SKIP_DOCKER" -eq 0 ]]; then
  echo "  container    $(docker inspect -f '{{.State.Status}}' mihomo-proxy 2>/dev/null || echo not-created)"
fi
echo
echo "check:"
echo "  docker compose -f \"$ROOT/docker-compose.yml\" logs -f"
echo "  docker run --rm --network telegram-proxy curlimages/curl:8.5.0 \\"
echo "    -sS --max-time 8 -x socks5h://proxy:11808 https://api.telegram.org"
