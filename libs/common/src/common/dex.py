from datetime import datetime
from typing import Optional
from web3 import Web3
from sqlalchemy.exc import IntegrityError
from common.db import SessionLocal
from db.models.models import LogJob, Swap


UNISWAP_V2_SWAP_SIGNATURE = (
    "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
)


UNISWAP_V3_SWAP_SIGNATURE = (
    "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
)

# Factory Addresses on Ethereum Mainnet
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
SUSHISWAP_FACTORY = "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"



class DexProcessor:
    web3: Web3
    _pool_token_cache: dict[str, tuple[str, str]]
    _pool_factory_cache: dict[str, str]

    def __init__(self, web3: Web3):
        self.web3 = web3
        self._pool_token_cache = {}
        self._pool_factory_cache = {}

    def process_uniswap_v2_swap(self, job: LogJob, topics: list[str]):
        """Process Uniswap V2 / SushiSwap Swap event"""
        if len(topics) < 3:
            return

        pool_address = job.get("address", "")
        sender = "0x" + topics[1][-40:]
        recipient = "0x" + topics[2][-40:]

        data = job.get("data", "0x")
        if not data or data == "0x":
            return

        try:
            data_bytes = bytes.fromhex(data[2:])

            amount0_in = int.from_bytes(data_bytes[0:32], "big")
            amount1_in = int.from_bytes(data_bytes[32:64], "big")
            amount0_out = int.from_bytes(data_bytes[64:96], "big")
            amount1_out = int.from_bytes(data_bytes[96:128], "big")

            print(
                f"Processing V2 Swap: Pool {pool_address[:10]}... - {amount0_in or amount0_out}/{amount1_in or amount1_out}"
            )

            token0, token1 = self._get_pool_tokens(pool_address)

            if not token0 or not token1:
                print(f"  Warning: Could not fetch pool tokens for {pool_address}")
                return

            factory_address = self._get_pool_factory(pool_address)
            dex_name = self._get_dex_from_factory(factory_address)

            if dex_name == "unknown":
                dex_name = "uniswap_v2"  # Default fallback for now. We should look to change this

            session = SessionLocal()
            try:
                swap = Swap(
                    transaction_hash=job.get("transaction_hash"),
                    log_index=job.get("log_index"),
                    block_number=job.get("block_number"),
                    block_timestamp=self._parse_timestamp(job.get("block_timestamp")),
                    transaction_index=job.get("transaction_index"),
                    dex_name=dex_name,
                    pool_address=pool_address.lower(),
                    token0_address=token0.lower(),
                    token1_address=token1.lower(),
                    amount0_in=str(amount0_in),
                    amount1_in=str(amount1_in),
                    amount0_out=str(amount0_out),
                    amount1_out=str(amount1_out),
                    sender=sender.lower(),
                    recipient=recipient.lower(),
                )

                session.add(swap)
                session.commit()
                print(f"Indexed {dex_name} swap")

            except IntegrityError:
                session.rollback()
            except Exception as e:
                session.rollback()
                print(f"Error processing V2 swap: {e}")
            finally:
                session.close()

        except Exception as e:
            print(f"Error decoding V2 swap data: {e}")

    def process_uniswap_v3_swap(self, job: LogJob, topics: list[str]):
        """Process Uniswap V3 Swap event"""
        if len(topics) < 3:
            return

        pool_address = job.get("address", "")
        sender = "0x" + topics[1][-40:]
        recipient = "0x" + topics[2][-40:]

        data = job.get("data", "0x")
        if not data or data == "0x":
            return

        try:
            data_bytes = bytes.fromhex(data[2:])

            amount0 = int.from_bytes(data_bytes[0:32], "big", signed=True)
            amount1 = int.from_bytes(data_bytes[32:64], "big", signed=True)
            sqrt_price_x96 = int.from_bytes(data_bytes[64:96], "big")
            liquidity = int.from_bytes(data_bytes[96:128], "big")
            tick = int.from_bytes(data_bytes[128:160], "big", signed=True)

            amount0_in = str(abs(amount0)) if amount0 < 0 else "0"
            amount0_out = str(amount0) if amount0 > 0 else "0"
            amount1_in = str(abs(amount1)) if amount1 < 0 else "0"
            amount1_out = str(amount1) if amount1 > 0 else "0"

            print(f"Processing V3 Swap: Pool {pool_address[:10]}... - {amount0_in or amount0_out}/{amount1_in or amount1_out}")

            token0, token1 = self._get_pool_tokens(pool_address)

            if not token0 or not token1:
                print(f"Warning: Could not fetch pool tokens for {pool_address}")
                return

            session = SessionLocal()
            try:
                swap = Swap(
                    transaction_hash=job.get("transaction_hash"),
                    log_index=job.get("log_index"),
                    block_number=job.get("block_number"),
                    block_timestamp=self._parse_timestamp(job.get("block_timestamp")),
                    transaction_index=job.get("transaction_index"),
                    dex_name="uniswap_v3",
                    pool_address=pool_address.lower(),
                    token0_address=token0.lower(),
                    token1_address=token1.lower(),
                    amount0_in=amount0_in,
                    amount1_in=amount1_in,
                    amount0_out=amount0_out,
                    amount1_out=amount1_out,
                    sender=sender.lower(),
                    recipient=recipient.lower(),
                    sqrt_price_x96=str(sqrt_price_x96),
                    liquidity=str(liquidity),
                    tick=tick,
                )

                session.add(swap)
                session.commit()
                print(f"Indexed V3 swap")

            except IntegrityError:
                session.rollback()
            except Exception as e:
                session.rollback()
                print(f"Error processing V3 swap: {e}")
            finally:
                session.close()

        except Exception as e:
            print(f"Error decoding V3 swap data: {e}")

    def _get_pool_tokens(self, pool_address: str) -> tuple[str, str]:
        """
        Get token0 and token1 addresses from a Uniswap pool.
        Results are cached to avoid repeated RPC calls.
        """
        pool_lower = pool_address.lower()
        if pool_lower in self._pool_token_cache:
            return self._pool_token_cache[pool_lower]

        pool_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "token0",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token1",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function",
            },
        ]

        try:
            pool_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(pool_address), abi=pool_abi
            )
            token0 = pool_contract.functions.token0().call()
            token1 = pool_contract.functions.token1().call()

            self._pool_token_cache[pool_lower] = (token0, token1)

            return (token0, token1)
        except Exception as e:
            print(f"Could not fetch pool tokens for {pool_address}: {e}")
            return ("", "")

    def _get_pool_factory(self, pool_address: str) -> Optional[str]:
        """Get factory address from a pool contract"""
        pool_lower = pool_address.lower()

        if pool_lower in self._pool_factory_cache:
            return self._pool_factory_cache[pool_lower]

        factory_abi = [
            {
                "inputs": [],
                "name": "factory",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        try:
            pool_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(pool_address), abi=factory_abi
            )
            factory = pool_contract.functions.factory().call()
            self._pool_factory_cache[pool_lower] = factory
            return factory
        except Exception as e:
            print(f"Could not fetch pool factory for {pool_address}: {e}")
            return None

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

    def _get_dex_from_factory(factory_address: str) -> str:
        """Get DEX name from factory address"""
        if not factory_address:
            return "unknown"

        factory_lower = factory_address.lower()

        if factory_lower == UNISWAP_V2_FACTORY.lower():
            return "uniswap_v2"
        elif factory_lower == SUSHISWAP_FACTORY.lower():
            return "sushiswap"
        elif factory_lower == UNISWAP_V3_FACTORY.lower():
            return "uniswap_v3"

        return "unknown"