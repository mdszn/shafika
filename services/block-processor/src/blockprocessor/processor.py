import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from web3 import Web3
from web3.types import BlockData
from dotenv import load_dotenv
from common.queue import RedisQueueManager
from common.db import SessionLocal
from db.models.models import Block, Transaction, WorkerStatus
from common.failedjob import FailedJobManager


class BlockProcessor:
  web3: Web3
  queue: RedisQueueManager
  queue_name: str
  executor: ThreadPoolExecutor
  failed_job: FailedJobManager

  def __init__(self, queue_name: str = "blocks", max_workers: int = 10):
    load_dotenv()
    http_url = os.getenv("ETH_HTTP_URL")
    self.web3 = Web3(Web3.HTTPProvider(http_url))
    self.queue = RedisQueueManager()
    self.queue_name = queue_name
    self.executor = ThreadPoolExecutor(max_workers=max_workers)
    self.failed_job = FailedJobManager(queue_name, 'process_block')

  def run(self):
    print(f"Worker listening on queue '{self.queue_name}'...")
    while True:
      job_id, job = self.queue.blocking_pop_json(self.queue_name)
      
      if not job:
        if job_id:
          print(f"Job {job_id} data missing or expired")
        continue
      
      block_number = job.get("block_number")
      block_hash = job.get("block_hash")
      print(f"Processing Block {block_number}")
      
      try:
        self.process_block(block_number, block_hash)
        self.queue.delete_job(job_id)
      except Exception as e:
        print(f"Error processing block {block_number}: {e}")
        if self.failed_job.record(job_id, job, str(e)):
          self.queue.delete_job(job_id)
        else:
          print(f"CRITICAL: Could not record failure for {job_id} - left in Redis")
  
  def process_block(self, block_number: int, block_hash: str):
    """Fetch block, parse txs, write to DB."""
    session = SessionLocal()
    block_record = None
    
    try:
      block_record = Block(
        block_number=block_number,
        block_hash=block_hash,
        worker_status=WorkerStatus.PROCESSING
      )
      session.add(block_record)
      session.commit()
      
      block = self.web3.eth.get_block(block_number, full_transactions=True)
      block_ts = datetime.fromtimestamp(block['timestamp'])
      tx_count = len(block['transactions'])
      print(f"  Processing {tx_count} txs from block {block_number}")
      
      futures = []
      for tx in block['transactions']:
        future = self.executor.submit(self._parse_transaction, tx, block_number, block_hash, block_ts)
        futures.append(future)
      
      for future in as_completed(futures):
        try:
          tx_model = future.result()
          session.add(tx_model)
        except Exception as e:
          print(f"  Error parsing tx: {e}")
      
      block_record.worker_status = WorkerStatus.DONE
      session.commit()
      print(f"  Block {block_number} completed ({tx_count} txs)")
      
    except Exception as e:
      session.rollback()
      self._mark_error(session, block_record, block_number, e)
    finally:
      session.close()

  def _parse_transaction(self, tx: BlockData, block_number, block_hash, block_ts):
    """Parse a single transaction (runs in thread pool)."""
    return Transaction(
      tx_hash=tx['hash'].hex(),
      block_number=block_number,
      block_hash=block_hash,
      block_timestamp=block_ts,
      from_address=tx.get('from'),
      to_address=tx.get('to'),
      value=int(tx['value']),
      gas_used=tx.get('gas'),
      gas_price=int(tx.get('gasPrice', 0)),
      input=tx.get('input'),
      status=1
    )

  def _mark_error(self, session: Session, block_record, block_number, error):
    """Mark block as error in DB."""
    try:
      if block_record:
        block_record.worker_status = WorkerStatus.ERROR
        session.commit()
    except Exception:
      pass
    print(f"Error processing block {block_number}: {error}")

