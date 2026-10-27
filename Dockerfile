FROM python:3.15.2-alpine@sha256:827d76cd0da4f700a703df95e7a70fec2ecc7fa9fd528638ab2e8aa96fbf8e0e

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
