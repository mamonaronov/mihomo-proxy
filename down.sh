#!/usr/bin/env bash
# Stop mihomo-proxy and remove its systemd unit.
# Does not delete ./data, images, volumes, or the docker network.
set -euo pipefail

UNIT="mihomo-proxy.service"
UNIT_PATH="/etc/systemd/system/${UNIT}"
WANTS_PATH="/etc/systemd/system/multi-user.target.wants/${UNIT}"

usage() {
  cat <<EOF
Usage: $(basename "$0")

Stops ${UNIT} (ExecStop runs docker compose stop), disables it,
and removes ${UNIT_PATH}.

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

need_cmd systemctl
if [[ "$(id -u)" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
  echo "error: need root or sudo to remove the systemd unit" >&2
  exit 1
fi

if systemctl cat "$UNIT" >/dev/null 2>&1; then
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

echo
echo "done"
echo "  unit     removed"
echo "  data     left in place"
