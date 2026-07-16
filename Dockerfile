FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for potential ML/nlp features
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for layer caching
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy the rest of the application
COPY . .

# Expose API port
EXPOSE 8000

# Default: run API server (override with CMD if needed)
CMD ["python", "cli.py", "api"]
