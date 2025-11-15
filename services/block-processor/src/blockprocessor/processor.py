import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from web3 import Web3
from web3.types import BlockData, TxData
from typing import cast
from dotenv import load_dotenv
from common.queue import RedisQueueManager
from common.db import SessionLocal
from db.models.models import Block, Transaction, WorkerStatus, JobType
from common.failedjob import FailedJobManager
from common.token import TokenMetadata
from requests.exceptions import HTTPError


class BlockProcessor:
    web3: Web3
    queue: RedisQueueManager
    queue_name: str
    executor: ThreadPoolExecutor
    failed_job: FailedJobManager

    def __init__(self, queue_name: str = "blocks", max_workers: int = 1):
        load_dotenv()
        http_url = os.getenv("ETH_HTTP_URL")
        self.web3 = Web3(Web3.HTTPProvider(http_url))
        self.queue = RedisQueueManager()
        self.queue_name = queue_name
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.failed_job = FailedJobManager(queue_name, JobType.BLOCK)
        self.token = TokenMetadata(self.web3)

    def run(self):
        print(f"Worker listening on queue '{self.queue_name}'...")
        while True:
            job_id, job = self.queue.bl_pop_block(self.queue_name)

            if not job:
                if job_id:
                    print(f"Job {job_id} data missing or expired")
                continue

            if not isinstance(job_id, str):
                continue

            block_number = job.get("block_number")
            block_hash = job.get("block_hash")
            block_status = job.get("status")
            is_retry = block_status == "retrying"

            if is_retry:
                print(f"Processing Block {block_number} (RETRY)")
            else:
                print(f"Processing Block {block_number}")

            try:
                self.process_block(block_number, block_hash, block_status)
                self.queue.delete_job(job_id)

                # If this was a retry, remove from failed_jobs table
                if is_retry:
                    if self.failed_job.remove_failed_block_record(job_id):
                        print(f"  Removed {job_id} from failed_jobs table")
                    else:
                        print(
                            f"  Warning: Could not remove {job_id} from failed_jobs table"
                        )
            except Exception as e:
                print(f"Error processing block {block_number}: {e}")
                if self.failed_job.record(job_id, job, str(e)):
                    self.queue.delete_job(job_id)
                else:
                    print(
                        f"CRITICAL: Could not record failure for {job_id} - left in Redis"
                    )

    def _fetch_block_with_retry(self, block_number: int, max_retries: int = 5):
        """Fetch block from Web3 with exponential backoff for rate limiting."""
        for attempt in range(max_retries):
            try:
                return self.web3.eth.get_block(block_number, full_transactions=True)
            except HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = (2**attempt) + (attempt * 0.5)  # Exponential backoff
                    print(
                        f"  Rate limited (429) on block {block_number}, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    if attempt == max_retries - 1:
                        raise
                else:
                    raise
            except Exception as e:
                # For non-rate-limit errors, fail immediately
                raise

    def process_block(self, block_number: int, block_hash: str, block_status: str):
        """Fetch block, parse txs, write to DB."""
        session = SessionLocal()
        block_record = None

        try:
            # For new blocks, create the record
            if block_status == "new":
                block_record = Block(
                    block_number=block_number,
                    block_hash=block_hash,
                    worker_status=WorkerStatus.PROCESSING,
                )
                session.add(block_record)
            # For retries, fetch existing record to update in same transaction
            else:
                block_record = (
                    session.query(Block)
                    .filter(Block.block_number == block_number)
                    .first()
                )

            block = self._fetch_block_with_retry(block_number)
            block_ts = datetime.fromtimestamp(block["timestamp"])  # pyright: ignore - always present
            tx_count = len(block["transactions"])  # pyright: ignore - always present
            print(f"  Processing {tx_count} txs from block {block_number}")

            futures = []
            for tx in block["transactions"]:  # pyright: ignore - always present
                tx_data = cast(TxData, tx)
                future = self.executor.submit(
                    self._parse_transaction, tx_data, block_number, block_hash, block_ts
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    tx_model = future.result()
                    session.add(tx_model)
                except Exception as e:
                    print(f"  Error parsing tx: {e}")

            # Update block status to DONE (for both new and retry)
            if block_record:
                block_record.worker_status = WorkerStatus.DONE  # pyright: ignore

            session.commit()
            print(f"  Block {block_number} completed ({tx_count} txs)")

        except Exception as e:
            session.rollback()
            self._mark_error(session, block_record, block_number, e)
            raise
        finally:
            session.close()

    def _parse_transaction(self, tx: TxData, block_number, block_hash, block_ts):
        """Parse a single transaction (runs in thread pool)."""

        eth_price = self.token.get_eth_price(self.queue.client)

        tx_value = int(tx["value"])  # pyright: ignore - always present in full tx
        wei = self.web3.from_wei(tx_value, "ether")

        value_usd = float(wei) * eth_price if eth_price else None

        return Transaction(
            tx_hash=tx["hash"].hex(),  # pyright: ignore - always present in full tx
            block_number=block_number,
            block_hash=block_hash,
            block_timestamp=block_ts,
            from_address=tx.get("from"),
            to_address=tx.get("to"),
            value=tx_value,
            value_usd=value_usd,
            gas_used=tx.get("gas"),
            gas_price=int(tx.get("gasPrice", 0)),
            input=tx.get("input"),
            status=1,
        )

    def _mark_error(self, session: Session, block_record, block_number, error):
        """Mark block as error in DB."""
        try:
            if block_record:
                block_record.worker_status = WorkerStatus.ERROR  # pyright: ignore
                session.commit()
        except Exception:
            pass
        print(f"Error processing block {block_number}: {error}")
