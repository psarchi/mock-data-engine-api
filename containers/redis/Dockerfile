FROM redis:7-alpine

RUN apk add --no-cache redis

RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'exec redis-server \' >> /entrypoint.sh && \
    echo '  --appendonly yes \' >> /entrypoint.sh && \
    echo '  --notify-keyspace-events AKE \' >> /entrypoint.sh && \
    echo '  --maxmemory ${REDIS_MAXMEMORY:-10gb} \' >> /entrypoint.sh && \
    echo '  --maxmemory-policy ${REDIS_MAXMEMORY_POLICY:-allkeys-lru}' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

EXPOSE 6379

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD redis-cli ping || exit 1

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
