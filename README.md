# PiHole v6 Exporter

![Docker Pulls](https://img.shields.io/badge/docker-ghcr.io-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Prometheus exporter for Pi-hole version 6, with support for HTTP/HTTPS and configurable ports.

## Why This Exporter?

Pi-hole v6 (released February 2025) introduced session-based authentication, breaking compatibility with existing exporters that used static API tokens. This exporter implements the new authentication flow with automatic session management and re-authentication on expiry.

## Features

- Compatible with Pi-hole v6 session-based authentication
- Configurable protocol (HTTP/HTTPS)
- Configurable PiHole port
- Exports comprehensive metrics including:
  - Query counts by type, status, and reply
  - Client statistics
  - Upstream DNS statistics
  - Blocklist statistics
  - Per-minute query metrics

## Usage

### Docker

```bash
docker run -p 9617:9617 ghcr.io/mosher-labs/pihole6-exporter:latest \
  -H pihole.example.com \
  --pihole-port 80 \
  --protocol http \
  -k your-api-token
```

### Kubernetes

**Important:** Pi-hole v6 limits concurrent API sessions. Use `replicas: 1` to avoid `api_seats_exceeded` errors.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pihole-exporter
spec:
  replicas: 1  # Required: Pi-hole v6 API session limits
  template:
    spec:
      containers:
        - name: pihole-exporter
          image: ghcr.io/mosher-labs/pihole6-exporter:latest
          args:
            - "-H"
            - "pihole-web.pihole.svc.cluster.local"
            - "--pihole-port"
            - "80"
            - "--protocol"
            - "http"
          env:
            - name: PIHOLE_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: pihole-password
                  key: password
          ports:
            - containerPort: 9617
              name: metrics
```

## Command-Line Arguments

- `-H, --host`: PiHole hostname/IP (default: localhost)
- `-p, --port`: Exporter port (default: 9617)
- `--pihole-port`: PiHole API port (default: 80)
- `--protocol`: Protocol to use - http or https (default: http)
- `-k, --key`: Authentication token (optional, for authenticated PiHole instances)

## Environment Variables

The exporter can also read the API token from the `PIHOLE_API_TOKEN` environment variable.

## Metrics

All metrics are prefixed with `pihole_`:

- `pihole_query_by_type`: Query counts by DNS record type (24h)
- `pihole_query_by_status`: Query counts by status (24h)
- `pihole_query_replies`: Reply counts by type (24h)
- `pihole_query_count`: Total query statistics (24h)
- `pihole_client_count`: Client statistics
- `pihole_domains_being_blocked`: Number of blocked domains
- `pihole_query_upstream_count`: Upstream DNS statistics (24h)
- `pihole_query_type_1m`: Query types (last minute)
- `pihole_query_status_1m`: Query status (last minute)
- `pihole_query_reply_1m`: Reply types (last minute)
- `pihole_query_client_1m`: Client activity (last minute)
- `pihole_query_upstream_1m`: Upstream activity (last minute)

## Docker Image

```bash
docker pull ghcr.io/mosher-labs/pihole6-exporter:latest
```

Available on GitHub Container Registry with automatic builds on every commit.

## Credits

Based on [bazmonk/pihole6_exporter](https://github.com/bazmonk/pihole6_exporter) with
modifications for HTTP support, automatic session re-authentication, and Kubernetes compatibility.

## License

MIT License
