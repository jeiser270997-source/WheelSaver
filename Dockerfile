FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy entire project first (pip install -e . needs source)
COPY . .

# Install package and dependencies
RUN pip install --no-cache-dir -e ".[audit]"

# Expose API port
EXPOSE 8000

# Default: run API server (override with CMD if needed)
CMD ["python", "cli.py", "api"]
