# Multi-stage build for Python API service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared dependencies
COPY db /app/db
COPY libs/common /app/libs/common

# Install common dependencies
RUN pip install --no-cache-dir -e /app/libs/common

# Copy service files
COPY services/api/pyproject.toml /app/
COPY services/api/gunicorn.conf.py /app/
COPY services/api/src /app/src

# Install service
RUN pip install --no-cache-dir -e /app

# Set Python path
ENV PYTHONPATH=/app:/app/db:/app/libs/common/src

# Run the API server with Gunicorn (production WSGI server)
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "api.server:app"]

