FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (build-only; purged after pip install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy entire project first (pip install -e . needs source)
COPY . .

# Install package and dependencies, then purge build toolchain (least privilege)
RUN pip install --no-cache-dir -e ".[audit]" \
    && apt-get purge -y --auto-remove gcc \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/pip

# Non-root user
RUN useradd --create-home --uid 1000 wheelsaver \
    && mkdir -p /home/wheelsaver/.wheelsaver \
    && chown -R wheelsaver:wheelsaver /app /home/wheelsaver

USER wheelsaver

# Expose API port
EXPOSE 8000

# Default: run API server (override with CMD if needed)
CMD ["python", "cli.py", "api"]
