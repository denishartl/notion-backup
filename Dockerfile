# ABOUTME: Docker image for notion-backup service.
# ABOUTME: ARM-compatible Python container for Raspberry Pi deployment.

FROM python:3.11-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy source code and project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir .

# Create data directories owned by the non-root user. Pre-creating /data/backups
# means a named volume mounted there inherits appuser ownership instead of root.
RUN mkdir -p /data/backups /data/logs && chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

EXPOSE 9101

# Default command
ENTRYPOINT ["python", "-m", "notion_backup"]
CMD ["serve"]
