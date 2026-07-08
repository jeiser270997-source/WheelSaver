FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose API port
EXPOSE 8000

# Default command: launch API
CMD ["python", "cli.py", "api", "--host", "0.0.0.0", "--port", "8000"]
