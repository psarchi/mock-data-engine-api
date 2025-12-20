# Security Policy

## ⚠️ Important Security Notice

**This software is designed for internal testing and development environments only.**

**DO NOT expose this service to the public internet without implementing additional security measures.** The default configuration prioritizes ease of use and performance over security, making it unsuitable for public-facing deployments.

### Why This Software Should Not Be Publicly Exposed:

- **No rate limiting** on REST endpoints (only WebSocket streaming)
- **No authentication** on WebSocket endpoints (designed for internal use)
- **No request size limits** configured by default
- **Admin endpoints** allow configuration changes and schema management
- **CORS wide open** by default (`allow_origins=["*"]`)
- **Default credentials** in `.env.example` must be changed
- **No input sanitization** for schema names and parameters

### Recommended Use Cases:
- Internal testing environments behind VPN/firewall
- Local development on localhost
- CI/CD pipelines for testing data quality
- Isolated development networks

### If you must deploy externally:
- Enable `SECURITY_MODE=token` and configure API key authentication
- Add a reverse proxy (nginx/Traefik) with TLS, rate limiting, and authentication
- Restrict CORS origins to specific domains
- Use network policies to limit access to admin endpoints
- Change all default credentials
- Add request size limits and timeouts

---

## Reporting Security Issues

If you discover a security vulnerability in this project, please report it via email to:

**[achikochachanidze@gmail.com](mailto:achikochachanidze@gmail.com)**

We take security seriously and will respond to legitimate reports within 48 hours.
