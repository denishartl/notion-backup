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

# Create data directory
RUN mkdir -p /data && chown appuser:appuser /data

# Switch to non-root user
USER appuser

# Default command
ENTRYPOINT ["python", "-m", "notion_backup"]
CMD ["serve"]
