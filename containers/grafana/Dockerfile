FROM grafana/grafana:latest

USER root

# Copy provisioning configurations
COPY provisioning /etc/grafana/provisioning
COPY dashboards /var/lib/grafana/dashboards

# Fix permissions (grafana user is UID 472)
RUN chown -R 472:472 /etc/grafana/provisioning /var/lib/grafana/dashboards && \
    chmod -R 755 /etc/grafana/provisioning /var/lib/grafana/dashboards

# Set environment variables for Grafana
ENV GF_AUTH_ANONYMOUS_ENABLED=true
ENV GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin

USER 472

# Expose Grafana port
EXPOSE 3000

# Use default entrypoint from base image
