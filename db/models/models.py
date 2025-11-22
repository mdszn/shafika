from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    TIMESTAMP,
    Boolean,
    JSON,
    func,
    Numeric,
    Float,
    SmallInteger,
    Integer,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import Enum as SQLEnum
from enum import Enum
from typing import TypedDict

Base = declarative_base()


class WorkerStatus(Enum):
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
    RETRYING = "retrying"


class JobType(Enum):
    BLOCK = "process_block"
    LOG = "process_log"


class BlockJob(TypedDict, total=True):
    job_type: str  # JobType enum value (e.g., 'process_block')
    block_number: int
    block_hash: str
    status: str


class LogJob(TypedDict, total=True):
    job_type: str  # JobType enum value (e.g., 'process_log')
    address: str
    block_number: int
    block_hash: str
    block_timestamp: int
    data: str
    log_index: int
    topics: list[str]
    transaction_hash: str
    transaction_index: int


class Block(Base):
    __tablename__ = "blocks"
    block_number = Column(BigInteger, primary_key=True)
    block_hash = Column(Text, nullable=False)
    canonical = Column(Boolean, default=True)  # Need logic for this
    processed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    worker_id = Column(String, nullable=True)
    worker_status = Column(SQLEnum(WorkerStatus))
    extra = Column(JSON, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    tx_hash = Column(String(66), primary_key=True)
    block_number = Column(BigInteger, nullable=False, index=True)
    block_hash = Column(String(66), nullable=False)
    block_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    from_address = Column(String(42), index=True)
    to_address = Column(String(42), index=True)
    value = Column(Numeric(38, 0))
    value_usd = Column(Float)
    gas_used = Column(BigInteger)
    gas_price = Column(Numeric(38, 0))
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
    token_type = Column(Text, default="erc20")
    token_symbol = Column(Text, nullable=True)
    token_decimals = Column(SmallInteger, nullable=True)
    token_id = Column(Numeric(78, 0), nullable=True)
    from_address = Column(String(42), nullable=True, index=True)
    to_address = Column(String(42), nullable=True, index=True)
    amount = Column(Numeric(78, 0), nullable=False)
    normalized_amount = Column(Numeric(38, 8), nullable=True)
    amount_usd = Column(Float, nullable=True)  # Need logic for this
    price_source = Column(Text, nullable=True)
    price_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)
    receipt_status = Column(SmallInteger, nullable=True)  # Need logic for this
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


class Contract(Base):
    __tablename__ = "contracts"
    contract_address = Column(String(42), primary_key=True)
    deployer_address = Column(String(42), nullable=False, index=True)
    deployment_tx_hash = Column(String(66), nullable=False)
    deployment_block_number = Column(BigInteger, nullable=False, index=True)
    deployment_timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    bytecode_hash = Column(String(66), nullable=True)  # keccak256 of bytecode
    is_verified = Column(Boolean, default=False)
    contract_name = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Approval(Base):
    __tablename__ = "approvals"
    tx_hash = Column(String(66), nullable=False, primary_key=True)
    log_index = Column(BigInteger, nullable=False, primary_key=True)
    block_number = Column(BigInteger, nullable=False, index=True)
    block_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    token_address = Column(String(42), nullable=False, index=True)
    owner = Column(String(42), nullable=False, index=True)
    spender = Column(String(42), nullable=False, index=True)
    value = Column(Numeric(78, 0), nullable=False)


class NftMetadata(Base):
    __tablename__ = "nft_metadata"
    token_address = Column(String(42), primary_key=True)
    token_id = Column(Numeric(78, 0), primary_key=True)

    # On-chain data
    token_uri = Column(Text, nullable=True)
    owner = Column(String(42), index=True)

    # Off-chain metadata (fetched from token_uri)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    external_url = Column(Text, nullable=True)
    animation_url = Column(Text, nullable=True)
    attributes = Column(JSON, nullable=True)
    
    metadata_fetched = Column(Boolean, default=False, index=True)
    metadata_fetch_failed = Column(Boolean, default=False)
    metadata_fetch_error = Column(Text, nullable=True)
    last_fetched_at = Column(TIMESTAMP(timezone=True), nullable=True)
    first_seen_block = Column(BigInteger, nullable=False, index=True)
    first_seen_tx = Column(String(66), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class AddressStats(Base):
    __tablename__ = "address_stats"
    address = Column(String(42), primary_key=True)
    first_seen_block = Column(BigInteger, nullable=False)
    last_seen_block = Column(BigInteger, nullable=False, index=True)
    tx_count = Column(Integer, default=0)
    eth_received = Column(Numeric(38, 0), default=0)
    eth_sent = Column(Numeric(38, 0), default=0)
    contract_deployments = Column(Integer, default=0)
    token_transfers_sent = Column(Integer, default=0)
    token_transfers_received = Column(Integer, default=0)
    is_contract = Column(Boolean, default=False)
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FailedJob(Base):
    __tablename__ = "failed_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False)
    queue_name = Column(String(50), nullable=False)
    job_type = Column(SQLEnum(JobType), nullable=False)
    data = Column(JSON, nullable=False)
    error = Column(Text, nullable=True)
    failed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    retries = Column(Integer, default=0)
    last_retry_at = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.ERROR)
    worker_id = Column(Text, nullable=True)
