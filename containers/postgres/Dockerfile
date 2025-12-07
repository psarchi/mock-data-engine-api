FROM postgres:15-alpine

RUN apk add --no-cache postgresql-client

COPY migrations /docker-entrypoint-initdb.d/

EXPOSE 5432

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD pg_isready -U ${POSTGRES_USER:-postgres} || exit 1

# CMD ["postgres"]
