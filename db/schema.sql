CREATE TABLE IF NOT EXISTS blocks (
  block_number BIGINT PRIMARY KEY,
  block_hash TEXT NOT NULL,
  canonical BOOLEAN DEFAULT TRUE,
  processed_at TIMESTAMPTZ DEFAULT now(),
  worker_id TEXT,
  worker_status TEXT NOT NULL DEFAULT 'done',
  extra JSONB
);

CREATE INDEX IF NOT EXISTS idx_blocks_status ON blocks(worker_status, processed_at DESC);

CREATE TABLE IF NOT EXISTS transactions (
  tx_hash VARCHAR(66) PRIMARY KEY,
  block_number BIGINT NOT NULL,
  block_hash VARCHAR(66) NOT NULL,
  block_timestamp TIMESTAMPTZ NOT NULL,
  from_address VARCHAR(42),
  to_address VARCHAR(42),
  value NUMERIC(38,0),
  value_usd DOUBLE PRECISION,
  gas_used BIGINT,
  gas_price NUMERIC(38,0),
  input TEXT,
  status SMALLINT
);

CREATE INDEX IF NOT EXISTS idx_transactions_block_number ON transactions(block_number);
CREATE INDEX IF NOT EXISTS idx_transactions_from ON transactions(from_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_to ON transactions(to_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(block_timestamp DESC);

CREATE TABLE IF NOT EXISTS transfers (
  tx_hash            VARCHAR(66)   NOT NULL,
  log_index          INT           NOT NULL,
  transaction_index  INT,                               -- position of tx in block
  block_number       BIGINT        NOT NULL,
  block_hash         VARCHAR(66)   NOT NULL,
  block_timestamp    TIMESTAMPTZ   NOT NULL,
  token_address      VARCHAR(42)   NOT NULL,
  token_type         TEXT          DEFAULT 'erc20',   -- 'erc20','erc721','erc1155','native','unknown'
  token_symbol       TEXT,
  token_decimals     SMALLINT,
  token_id           NUMERIC(78,0),                    -- nullable, for NFTs / ERC1155
  from_address       VARCHAR(42),
  to_address         VARCHAR(42),
  amount             NUMERIC(78,0) NOT NULL,           -- raw token base units
  normalized_amount  NUMERIC(38,8),                     -- human-friendly (amount / 10**decimals)
  amount_usd         DOUBLE PRECISION,                  -- usd value at timestamp
  price_source       TEXT,                              -- e.g. 'coingecko','oracle'
  price_timestamp    TIMESTAMPTZ,
  receipt_status     SMALLINT,                          -- tx receipt status 0/1
  raw_log            JSONB,
  inserted_at        TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (tx_hash, log_index)
);

CREATE INDEX IF NOT EXISTS idx_transfers_block_number ON transfers(block_number DESC);
CREATE INDEX IF NOT EXISTS idx_transfers_block_timestamp ON transfers(block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transfers_token_address ON transfers(token_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transfers_from_address ON transfers(from_address, block_timestamp DESC) WHERE from_address IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transfers_to_address ON transfers(to_address, block_timestamp DESC) WHERE to_address IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transfers_token_type ON transfers(token_type, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transfers_token_id ON transfers(token_address, token_id) WHERE token_id IS NOT NULL;  -- for NFT lookups
CREATE INDEX IF NOT EXISTS idx_transfers_amount_usd ON transfers(amount_usd DESC NULLS LAST) WHERE amount_usd IS NOT NULL;  -- for top transfers

CREATE INDEX IF NOT EXISTS idx_transfers_raw_log ON transfers USING GIN(raw_log);
