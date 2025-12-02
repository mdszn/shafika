import os
from datetime import datetime
from typing import Optional

from common.db import SessionLocal
from common.dex import (UNISWAP_V2_SWAP_SIGNATURE, UNISWAP_V3_SWAP_SIGNATURE,
                        DexProcessor)
from common.failedjob import FailedJobManager
from common.nft import NftMetadataFetcher
from common.queue import RedisQueueManager
from common.token import TokenMetadata
from dotenv import load_dotenv
from eth_abi.abi import decode
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from web3 import Web3

from db.models.models import AddressStats, Approval, JobType, LogJob, Transfer

# Event signatures
TRANSFER_EVENT_SIGNATURE = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # ERC20/ERC721
)
ERC1155_TRANSFER_SINGLE = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"  # TransferSingle
ERC1155_TRANSFER_BATCH = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"  # TransferBatch
APPROVAL_EVENT_SIGNATURE = (
    "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
)


class LogProcessor:
    web3: Web3
    redis_client: RedisQueueManager
    queue_name: str
    token_service: TokenMetadata
    failed_job: FailedJobManager
    dex_processor: DexProcessor
    nft_fetcher: NftMetadataFetcher

    def __init__(self, queue_name: str = "logs"):
        load_dotenv()
        http_url = os.getenv("ETH_HTTP_URL")
        self.web3 = Web3(Web3.HTTPProvider(http_url))
        self.redis_client = RedisQueueManager()
        self.queue_name = queue_name
        self.token_service = TokenMetadata(self.web3)
        self.failed_job = FailedJobManager(queue_name, JobType.LOG)
        self.dex_processor = DexProcessor(self.web3)
        self.nft_fetcher = NftMetadataFetcher(self.web3)

    def run(self):
        print(f"Worker listening on queue '{self.queue_name}'...")
        while True:
            job_id, job = self.redis_client.bl_pop_log(self.queue_name)

            if not job:
                if job_id:
                    print(f"Job {job_id} data missing or expired")
                continue

            if not isinstance(job_id, str):
                continue

            log_status = job.get("status")
            is_retry = log_status == "retrying"

            try:
                self.process_log(job)
                self.redis_client.delete_job(job_id)

                if is_retry:
                    if self.failed_job.remove_failed_job(job_id):
                        print(f"Removed {job_id} from failed_jobs table")
                    else:
                        print(f"Could not remove {job_id} from failed_jobs table")
            except Exception as e:
                print("Error processing log for Job")
                if self.failed_job.record(job_id, job, str(e)):
                    self.redis_client.delete_job(job_id)
                else:
                    print(f"Could not record failure for {job_id} - left in Redis")

    def process_log(self, job: LogJob):
        """Process a single log event - dispatches to appropriate handler"""
        topics = job.get("topics", [])

        if not topics:
            return

        event_signature = topics[0]

        if event_signature == TRANSFER_EVENT_SIGNATURE:
            self._process_erc20_or_erc721_transfer(job, topics)
        elif event_signature == APPROVAL_EVENT_SIGNATURE:
            self._process_approval_event(job, topics)
        elif event_signature == ERC1155_TRANSFER_SINGLE:
            self._process_erc1155_single(job, topics)
        elif event_signature == ERC1155_TRANSFER_BATCH:
            self._process_erc1155_batch(job, topics)
        elif event_signature == UNISWAP_V2_SWAP_SIGNATURE:
            self.dex_processor.process_uniswap_v2_swap(job, topics)
        elif event_signature == UNISWAP_V3_SWAP_SIGNATURE:
            self.dex_processor.process_uniswap_v3_swap(job, topics)

    def _process_approval_event(self, job: LogJob, topics: list[str]):
        """Process ERC20 Approval event"""
        if len(topics) < 3:
            return

        tx_hash = job.get("transaction_hash")
        log_index = self._parse_log_index(job.get("log_index"))
        block_number = job.get("block_number")
        block_timestamp = self._parse_timestamp(job.get("block_timestamp"))
        token_address = job.get("address")

        owner = "0x" + topics[1][-40:]
        spender = "0x" + topics[2][-40:]

        data = job.get("data", "0x")
        if data and data != "0x":
            value = int(data, 16)
        else:
            value = 0

        session = SessionLocal()
        try:
            approval = Approval(
                tx_hash=tx_hash,
                log_index=log_index,
                block_number=block_number,
                block_timestamp=block_timestamp,
                token_address=token_address.lower(),
                owner=owner.lower(),
                spender=spender.lower(),
                value=value,
            )
            session.add(approval)
            session.commit()
        except IntegrityError:
            session.rollback()
        except Exception as e:
            session.rollback()
            print(f"  Error saving approval: {e}")
        finally:
            session.close()

    def _process_erc20_or_erc721_transfer(self, job: LogJob, topics: list[str]):
        """Process ERC20 or ERC721 Transfer event"""
        if len(topics) < 3:
            return

        token_address = job.get("address")
        tx_hash = job.get("transaction_hash")
        log_index = self._parse_log_index(job.get("log_index"))

        from_address = self._decode_address(topics[1])
        to_address = self._decode_address(topics[2])

        # Determine if ERC20 or ERC721
        data = job.get("data", "0x")
        token_id = None
        amount = 0
        token_type = "erc20"

        if len(topics) == 4:
            # ERC721: tokenId is indexed (in topics[3])
            token_type = "erc721"
            token_id = int(topics[3], 16)
            amount = 1  # NFTs are 1-of-1
        else:
            # ERC20: amount is in data
            token_type = "erc20"
            amount = int(data, 16) if data != "0x" else 0

        print(
            f"Processing {token_type.upper()} Transfer: {token_address[:10]}... in tx {tx_hash[:10]}..."
        )

        token_symbol, token_decimals = self.token_service.get_metadata(
            token_address, token_type
        )

        normalized_amount = None
        if token_type == "erc20" and token_decimals is not None and token_decimals > 0:
            normalized_amount = amount / (10**token_decimals)
        elif token_type == "erc721":
            normalized_amount = 1.0

        block_number = job.get("block_number")
        block_timestamp = self._parse_timestamp(job.get("block_timestamp"))

        self._save_transfer(
            tx_hash=tx_hash,
            log_index=log_index,
            transaction_index=self._parse_int(job.get("transaction_index")),
            block_number=block_number,
            block_hash=job.get("block_hash"),
            block_timestamp=block_timestamp,
            token_address=token_address.lower(),
            token_type=token_type,
            token_symbol=token_symbol,
            token_decimals=token_decimals,
            token_id=token_id,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            normalized_amount=normalized_amount,
            raw_log=job,
        )

        # Create NFT metadata record for ERC721
        if token_type == "erc721" and token_id is not None and to_address:
            self.nft_fetcher.create_nft_metadata(
                token_address=token_address.lower(),
                token_id=token_id,
                owner=to_address.lower(),
                block_number=block_number,
                tx_hash=tx_hash,
            )

    def _process_erc1155_single(self, job: LogJob, topics: list[str]):
        """Process ERC1155 TransferSingle event"""
        if len(topics) < 4:
            return

        token_address = job.get("address")
        tx_hash = job.get("transaction_hash")
        log_index = self._parse_log_index(job.get("log_index"))

        from_address = self._decode_address(topics[2])
        to_address = self._decode_address(topics[3])

        data = job.get("data", "0x")
        if data == "0x" or len(data) < 66:
            return

        token_id = int(data[2:66], 16)
        amount = int(data[66:130], 16) if len(data) >= 130 else 0

        print(
            f"Processing ERC1155 Single: {token_address[:10]}... token #{token_id} in tx {tx_hash[:10]}..."
        )

        token_symbol, _ = self.token_service.get_metadata(token_address, "erc1155")

        block_number = job.get("block_number")
        block_timestamp = self._parse_timestamp(job.get("block_timestamp"))

        self._save_transfer(
            tx_hash=tx_hash,
            log_index=log_index,
            transaction_index=self._parse_int(job.get("transaction_index")),
            block_number=block_number,
            block_hash=job.get("block_hash"),
            block_timestamp=block_timestamp,
            token_address=token_address.lower(),
            token_type="erc1155",
            token_symbol=token_symbol,
            token_decimals=None,
            token_id=token_id,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            normalized_amount=float(amount),
            raw_log=job,
        )

        # Create NFT metadata record for ERC1155
        if to_address:
            self.nft_fetcher.create_nft_metadata(
                token_address=token_address.lower(),
                token_id=token_id,
                owner=to_address.lower(),
                block_number=block_number,
                tx_hash=tx_hash,
            )

    def _process_erc1155_batch(self, job: LogJob, topics: list[str]):
        """Process ERC1155 TransferBatch event - creates multiple transfer records"""
        if len(topics) < 4:
            return

        token_address = job.get("address")
        tx_hash = job.get("transaction_hash")
        base_log_index = self._parse_log_index(job.get("log_index"))

        from_address = self._decode_address(topics[2])
        to_address = self._decode_address(topics[3])

        data = job.get("data", "0x")
        if data == "0x" or len(data) < 66:
            return

        try:

            data_bytes = bytes.fromhex(data[2:])

            decoded = decode(["uint256[]", "uint256[]"], data_bytes)
            ids = decoded[0]
            values = decoded[1]

            if len(ids) != len(values):
                print(
                    f"  Error: ERC1155 batch has mismatched arrays (ids: {len(ids)}, values: {len(values)})"
                )
                return

            print(
                f"Processing ERC1155 Batch: {token_address[:10]}... ({len(ids)} tokens) in tx {tx_hash[:10]}..."
            )

            token_symbol, _ = self.token_service.get_metadata(token_address, "erc1155")

            block_number = job.get("block_number")
            block_timestamp = self._parse_timestamp(job.get("block_timestamp"))

            for i, (token_id, amount) in enumerate(zip(ids, values)):
                # For batch transfers, we need unique log_index for each transfer
                # Use base_log_index + fractional offset (stored as int by multiplying)
                # Or we can use a composite key approach
                unique_log_index = base_log_index * 1000 + i

                self._save_transfer(
                    tx_hash=tx_hash,
                    log_index=unique_log_index,
                    transaction_index=self._parse_int(job.get("transaction_index")),
                    block_number=block_number,
                    block_hash=job.get("block_hash"),
                    block_timestamp=block_timestamp,
                    token_address=token_address.lower(),
                    token_type="erc1155",
                    token_symbol=token_symbol,
                    token_decimals=None,
                    token_id=token_id,
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    normalized_amount=float(amount),
                    raw_log=job,
                )

                if to_address:
                    self.nft_fetcher.create_nft_metadata(
                        token_address=token_address.lower(),
                        token_id=token_id,
                        owner=to_address.lower(),
                        block_number=block_number,
                        tx_hash=tx_hash,
                    )

            print(f"Saved {len(ids)} ERC1155 batch transfers")

        except Exception as e:
            print(f"Error decoding ERC1155 batch: {e}")
            raise

    def _save_transfer(self, **kwargs):
        """Save a transfer to the database"""
        transfer = Transfer(**kwargs)

        session = SessionLocal()
        try:
            session.add(transfer)

            # Update address stats for sender
            from_address = kwargs.get("from_address")
            to_address = kwargs.get("to_address")
            block_number = kwargs.get("block_number")
            zero_addr = "0x0000000000000000000000000000000000000000"

            updates = []
            if from_address and from_address != zero_addr:
                updates.append({"addr": from_address, "sent": True})

            if to_address and to_address != zero_addr:
                updates.append({"addr": to_address, "sent": False})

            updates.sort(key=lambda x: x["addr"])

            for update in updates:
                self._update_token_transfer_stats(
                    session, update["addr"], block_number, sent=update["sent"]
                )

            session.commit()

            from_addr = (
                kwargs.get("from_address", "")[:8]
                if kwargs.get("from_address")
                else "None"
            )
            to_addr = (
                kwargs.get("to_address", "")[:8] if kwargs.get("to_address") else "None"
            )
            amount = kwargs.get("normalized_amount")
            symbol = kwargs.get("token_symbol") or "???"
            token_type = kwargs.get("token_type", "").upper()
            token_id = kwargs.get("token_id")

            if token_id is not None:
                print(
                    f"Saved {token_type}: {from_addr}... → {to_addr}... (Token #{token_id}, {symbol})"
                )
            else:
                print(
                    f"Saved {token_type}: {from_addr}... → {to_addr}... ({amount} {symbol})"
                )
        except IntegrityError:
            session.rollback()
            print("Duplicate transfer (already processed)")
        except Exception as e:
            session.rollback()
            print(f"Error saving transfer: {e}")
            raise
        finally:
            session.close()

    def _update_token_transfer_stats(
        self, session: Session, address: str, block_number: int, sent: bool
    ):
        """Update token transfer counts for address using upsert to avoid deadlocks"""
        address_lower = address.lower()

        stmt = insert(AddressStats).values(
            address=address_lower,
            first_seen_block=block_number,
            last_seen_block=block_number,
            token_transfers_sent=1 if sent else 0,
            token_transfers_received=0 if sent else 1,
        )

        update_dict = {
            "last_seen_block": block_number,
            "updated_at": func.now(),
        }

        if sent:
            update_dict["token_transfers_sent"] = AddressStats.token_transfers_sent + 1
        else:
            update_dict["token_transfers_received"] = (
                AddressStats.token_transfers_received + 1
            )

        stmt = stmt.on_conflict_do_update(
            index_elements=["address"],
            set_=update_dict,
        )

        session.execute(stmt)

    def _decode_address(self, topic: str) -> Optional[str]:
        """Decode address from indexed topic (32 bytes padded)"""
        if not topic or len(topic) < 42:
            return None
        return "0x" + topic[-40:].lower()

    def _parse_log_index(self, log_index) -> int:
        """Parse log index from hex or int"""
        if isinstance(log_index, int):
            return log_index
        if isinstance(log_index, str):
            return int(log_index, 16)
        return 0

    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp from job data (hex, int, or None)"""
        if timestamp is None:
            return datetime.now()

        try:
            if isinstance(timestamp, str) and timestamp.startswith("0x"):
                timestamp_int = int(timestamp, 16)
            elif isinstance(timestamp, str):
                timestamp_int = int(timestamp)
            else:
                timestamp_int = timestamp

            return datetime.fromtimestamp(timestamp_int)
        except Exception as e:
            print(f"Could not parse timestamp {timestamp}: {e}")
            return datetime.now()

    def _parse_int(self, value) -> Optional[int]:
        """Parse hex or int to int"""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 16)
        return None
