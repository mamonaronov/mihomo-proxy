#!/usr/bin/env bash
# Stop the mihomo-proxy container and remove its systemd unit if installed.
# Also stops a container started with ./deploy.sh --once (no unit).
# Does not delete ./data, images, volumes, or the docker network.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
UNIT="mihomo-proxy.service"
UNIT_PATH="/etc/systemd/system/${UNIT}"
WANTS_PATH="/etc/systemd/system/multi-user.target.wants/${UNIT}"

usage() {
  cat <<EOF
Usage: $(basename "$0")

Stops the mihomo-proxy container with docker compose stop, including one
started by ./deploy.sh --once with no systemd unit.

If ${UNIT} is installed, stops it (ExecStop runs docker compose stop),
disables it, and removes ${UNIT_PATH}.

Leaves ./data, images, volumes, and the telegram-proxy network in place.
EOF
}

for arg in "$@"; do
  case "$arg" in
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

run_sudo() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

unit_loaded=0
if command -v systemctl >/dev/null 2>&1 && systemctl cat "$UNIT" >/dev/null 2>&1; then
  unit_loaded=1
fi

unit_files=0
if [[ -e "$UNIT_PATH" || -L "$WANTS_PATH" || -e "$WANTS_PATH" ]]; then
  unit_files=1
fi

if [[ "$unit_loaded" -eq 1 || "$unit_files" -eq 1 ]]; then
  need_cmd systemctl
  if [[ "$(id -u)" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
    echo "error: need root or sudo to remove the systemd unit" >&2
    exit 1
  fi

  if [[ "$unit_loaded" -eq 1 ]]; then
    echo "==> stopping $UNIT"
    if ! run_sudo systemctl stop "$UNIT"; then
      echo "warning: systemctl stop $UNIT failed; removing the unit anyway" >&2
    fi
    echo "==> disabling $UNIT"
    run_sudo systemctl disable "$UNIT"
  else
    echo "==> $UNIT is not loaded"
  fi

  if [[ -e "$UNIT_PATH" ]]; then
    echo "==> removing $UNIT_PATH"
    run_sudo rm -f "$UNIT_PATH"
  fi

  if [[ -L "$WANTS_PATH" || -e "$WANTS_PATH" ]]; then
    echo "==> removing $WANTS_PATH"
    run_sudo rm -f "$WANTS_PATH"
  fi

  echo "==> systemd daemon-reload"
  run_sudo systemctl daemon-reload
  run_sudo systemctl reset-failed "$UNIT" >/dev/null 2>&1 || true
else
  echo "==> $UNIT is not installed"
fi

need_cmd docker
echo "==> docker compose stop"
(
  cd "$ROOT"
  docker compose --project-directory "$ROOT" -f "$ROOT/docker-compose.yml" stop
)
running="$(docker inspect -f '{{.State.Running}}' mihomo-proxy 2>/dev/null || true)"
if [[ "$running" == "true" ]]; then
  echo "==> docker stop mihomo-proxy"
  docker stop mihomo-proxy
fi

echo
echo "done"
if [[ "$unit_loaded" -eq 1 || "$unit_files" -eq 1 ]]; then
  echo "  unit       removed"
else
  echo "  unit       not installed"
fi
echo "  container  $(docker inspect -f '{{.State.Status}}' mihomo-proxy 2>/dev/null || echo not-created)"
echo "  data       left in place"
