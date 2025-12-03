FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY db /app/db
COPY libs/common /app/libs/common
COPY scripts /app/scripts

RUN pip install --no-cache-dir -e /app/libs/common

COPY services/api/pyproject.toml /app/
COPY services/api/gunicorn.conf.py /app/
COPY services/api/src /app/src

RUN pip install --no-cache-dir -e /app

ENV PYTHONPATH=/app:/app/db:/app/libs/common/src

# Run the API server with Gunicorn (production WSGI server)
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "api.server:app"]

