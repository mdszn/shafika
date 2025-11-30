FROM python:3.11-slim

WORKDIR /app

COPY libs/common /app/libs/common
COPY db /app/db

COPY services/nft-metadata-worker /app/services/nft-metadata-worker

RUN pip install --no-cache-dir -e /app/libs/common
RUN pip install --no-cache-dir -e /app/services/nft-metadata-worker

WORKDIR /app

CMD ["python", "-m", "nftworker"]

