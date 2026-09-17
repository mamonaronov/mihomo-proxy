#!/bin/sh
set -euo pipefail

# Base image (metacubex/mihomo:latest): Alpine, ENTRYPOINT ["/mihomo"], no CMD.
# Default config dir is /root/.config/mihomo. We bind-mount ./data at /etc/mihomo
# and exec the original binary with -d so providers/cache stay on that volume.

TEMPLATE="/template/config.yaml"
RUNTIME="/etc/mihomo/config.yaml"

if [ ! -f "$TEMPLATE" ]; then
  printf '%s\n' "error: template not found: $TEMPLATE" >&2
  exit 1
fi

missing=0
for var in SUB1_URL SUB2_URL SUB3_URL SUB4_URL SUB5_URL MIHOMO_API_SECRET; do
  eval "val=\${$var-}"
  if [ -z "$val" ]; then
    printf '%s\n' "error: required variable $var is empty or unset" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  exit 1
fi

# A copied .env.example must not go live.
case "$MIHOMO_API_SECRET" in
  change-me|CHANGE-ME|changeme|replace-me|REPLACE_ME|replace_me)
    printf '%s\n' "error: MIHOMO_API_SECRET is a placeholder; generate one (openssl rand -hex 32)" >&2
    exit 1
    ;;
esac

# Optional providers stay commented in the template. envsubst still replaces
# placeholders inside # lines, so export empty defaults when unset.
SUB6_URL="${SUB6_URL:-}"
SUB7_URL="${SUB7_URL:-}"
SUB8_URL="${SUB8_URL:-}"
export SUB1_URL SUB2_URL SUB3_URL SUB4_URL SUB5_URL
export SUB6_URL SUB7_URL SUB8_URL
export MIHOMO_API_SECRET

mkdir -p /etc/mihomo/providers

envsubst '${SUB1_URL} ${SUB2_URL} ${SUB3_URL} ${SUB4_URL} ${SUB5_URL} ${SUB6_URL} ${SUB7_URL} ${SUB8_URL} ${MIHOMO_API_SECRET}' \
  < "$TEMPLATE" > "$RUNTIME"

if grep -E '\$\{(SUB[1-5]_URL|MIHOMO_API_SECRET)\}' "$RUNTIME" >/dev/null; then
  printf '%s\n' "error: unsubstituted placeholders remain in $RUNTIME" >&2
  grep -E '\$\{(SUB[1-5]_URL|MIHOMO_API_SECRET)\}' "$RUNTIME" >&2 || true
  exit 1
fi

if grep -Eq '^secret:[[:space:]]*""[[:space:]]*$' "$RUNTIME"; then
  printf '%s\n' "error: MIHOMO_API_SECRET is empty after substitution" >&2
  exit 1
fi

if ! grep -Eq '^secret:[[:space:]]*".+"[[:space:]]*$' "$RUNTIME"; then
  printf '%s\n' "error: secret is missing or empty in $RUNTIME" >&2
  exit 1
fi

exec /mihomo -d /etc/mihomo "$@"
