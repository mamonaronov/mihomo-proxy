FROM metacubex/mihomo:v1.19.31

# Alpine 3.24.1 (from the base image). envsubst is in Alpine's gettext package.
RUN apk add --no-cache gettext

# Fallback if compose is not used. Compose bind-mounts ./config.yaml over this.
COPY config.yaml /template/config.yaml
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Original image: ENTRYPOINT ["/mihomo"], no CMD, default dir /root/.config/mihomo.
# We generate /etc/mihomo/config.yaml and exec /mihomo -d /etc/mihomo.
ENTRYPOINT ["/docker-entrypoint.sh"]
