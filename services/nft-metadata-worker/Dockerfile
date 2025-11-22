FROM python:3.11-slim

WORKDIR /app

# Copy common library and db models
COPY libs/common /app/libs/common
COPY db /app/db

# Copy service code
COPY services/nft-metadata-worker /app/services/nft-metadata-worker

# Install dependencies
RUN pip install --no-cache-dir -e /app/libs/common
RUN pip install --no-cache-dir -e /app/services/nft-metadata-worker

WORKDIR /app

CMD ["python", "-m", "nftworker"]

