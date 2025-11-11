
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY db /app/db

COPY libs/common /app/libs/common

RUN pip install --no-cache-dir -e /app/libs/common

COPY services/block-poller/pyproject.toml /app/
COPY services/block-poller/src /app/src

RUN pip install --no-cache-dir -e /app

ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["python", "-m", "blockpoller"]

