FROM python:3.15.2-alpine@sha256:a0f2e268f2ce8f3709611a90054ec6a8ae31f6251f5896b8648b9bb99835e30a

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
