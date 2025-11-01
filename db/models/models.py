from sqlalchemy import (
    Column, BigInteger, String, Text, TIMESTAMP, Boolean, JSON, func,
    Numeric, Float, SmallInteger, Integer
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import Enum
import enum

Base = declarative_base()

class WorkerStatus(enum.Enum):
  PROCESSING = "processing"
  DONE = "done"
  ERROR = "error"
  

class Block(Base):
  __tablename__ = "blocks"
  block_number = Column(BigInteger, primary_key=True)
  block_hash = Column(Text, nullable=False)
  canonical = Column(Boolean, default=True) # Need logic for this
  processed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
  worker_id = Column(String, nullable=True)
  worker_status = Column(Enum(WorkerStatus))
  extra = Column(JSON, nullable=True)
  
class Transaction(Base):
  __tablename__ = "transactions"
  tx_hash = Column(String(66), primary_key=True)
  block_number = Column(BigInteger, nullable=False, index=True)
  block_hash = Column(String(66), nullable=False)
  block_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
  from_address = Column(String(42), index=True)
  to_address = Column(String(42), index=True)
  value = Column(Numeric(38,0))
  value_usd = Column(Float) # Need logic for this
  gas_used = Column(BigInteger)
  gas_price = Column(Numeric(38,0))
  input = Column(Text)
  status = Column(SmallInteger)

class Transfer(Base):
  __tablename__ = "transfers"
  tx_hash = Column(String(66), nullable=False, primary_key=True)
  log_index = Column(BigInteger, nullable=False, primary_key=True)
  transaction_index = Column(BigInteger, nullable=True)
  block_number = Column(BigInteger, nullable=False, index=True)
  block_hash = Column(String(66), nullable=False)
  block_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
  token_address = Column(String(42), nullable=False, index=True)
  token_type = Column(Text, default='erc20')
  token_symbol = Column(Text, nullable=True)
  token_decimals = Column(SmallInteger, nullable=True)
  token_id = Column(Numeric(78,0), nullable=True)
  from_address = Column(String(42), nullable=True, index=True)
  to_address = Column(String(42), nullable=True, index=True)
  amount = Column(Numeric(78,0), nullable=False)
  normalized_amount = Column(Numeric(38,8), nullable=True)
  amount_usd = Column(Float, nullable=True) # Need logic for this
  price_source = Column(Text, nullable=True)
  price_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)
  receipt_status = Column(SmallInteger, nullable=True) # Need logic for this
  raw_log = Column(JSON, nullable=True)
  inserted_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Token(Base):
  __tablename__ = "tokens"
  token_address = Column(String(42), primary_key=True)
  token_type = Column(Text, nullable=True)
  symbol = Column(Text, nullable=True)
  name = Column(Text, nullable=True)
  decimals = Column(SmallInteger, nullable=True)
  fetched_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
  failed = Column(Boolean, default=False)
  extra = Column(JSON, nullable=True)

class FailedJob(Base):
  __tablename__ = "failed_jobs"
  id = Column(Integer, primary_key=True, autoincrement=True)
  job_id = Column(String(100), unique=True, nullable=False)
  queue_name = Column(String(50), nullable=False)
  job_type = Column(String(50), nullable=False)
  data = Column(JSON, nullable=False)
  error = Column(Text, nullable=True)
  failed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
  retries = Column(Integer, default=0)
  last_retry_at = Column(TIMESTAMP(timezone=True), nullable=True)
  status = Column(String(20), default='failed')
  worker_id = Column(Text, nullable=True)