FROM python:3.14.8-alpine@sha256:f6a589d43c42b9e7f7dc67a12d37132491f362859a5d750607710cc56da3bc72

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
