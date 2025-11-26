FROM python:3.11-alpine

# Install dependencies
RUN pip install --no-cache-dir prometheus_client requests urllib3

# Copy the exporter script
COPY pihole6_exporter /usr/local/bin/pihole6_exporter
RUN chmod +x /usr/local/bin/pihole6_exporter

# Expose metrics port
EXPOSE 9617

# Run the exporter
ENTRYPOINT ["/usr/local/bin/pihole6_exporter"]
