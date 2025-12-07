FROM prom/prometheus:latest

USER root

COPY prometheus.yml /etc/prometheus/prometheus.yml

RUN chown nobody:nobody /etc/prometheus/prometheus.yml && \
    chmod 644 /etc/prometheus/prometheus.yml
USER nobody
EXPOSE 9090