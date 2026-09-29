FROM python:3.14.7-alpine@sha256:9e9fde4d32eedce0b661d9ab91e826b62dddf28e928c230ec55f1866cac66b01

# Install dependencies pinned by version and hash
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy the exporter script
COPY pihole6_exporter /usr/local/bin/pihole6_exporter
RUN chmod +x /usr/local/bin/pihole6_exporter

# Run as nobody: the exporter needs no root privileges, and 9617 is unprivileged.
USER 65534:65534

# Expose metrics port
EXPOSE 9617

# Run the exporter
ENTRYPOINT ["/usr/local/bin/pihole6_exporter"]
