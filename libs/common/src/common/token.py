from typing import Optional
from redis.client import Redis
from web3 import Web3
from .db import SessionLocal
from db.models.models import Token
import requests
import os
import redis


class TokenMetadata:
    """Service for fetching and caching token metadata (symbol, decimals, etc.)"""

    def __init__(self, web3: Web3):
        self.web3 = web3

    def get_metadata(self, token_address: str, token_type: str = "erc20"):
        """
        Get token symbol and decimals with 2-tier caching:
        1. Database cache (fast - uses PRIMARY KEY index)
        2. Blockchain call (slow - only if not in DB)
        """
        token_address_lower = token_address.lower()
        session = SessionLocal()
        try:
            token = (
                session.query(Token)
                .filter(Token.token_address == token_address_lower)
                .first()
            )

            if token:
                return (
                    token.symbol,
                    token.decimals,
                )
        finally:
            session.close()

        return self._fetch_from_blockchain(token_address_lower, token_type)

    def get_eth_price(self, redis_client: redis.Redis, ttl: int = 10):
        """Fetch ETH/USD Price from CryptoCompare"""

        if redis_client:
            cached_price = redis_client.get("eth_price")
            if cached_price:
                return float(cached_price)

        try:
            endpoint = "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD"

            response = requests.get(endpoint, timeout=10)
            response.raise_for_status()

            response_data = response.json()

            eth_usd = response_data.get("USD")

            if eth_usd is None:
                raise Exception("Missing 'USD' in API response")

            price = float(eth_usd)

            if redis_client:
                redis_client.setex("eth_price", ttl, price)

            return price

        except Exception as e:
            print(f"Error fetching ETH Price: {e}")
            return None

    def _fetch_from_blockchain(self, token_address: str, token_type: str):
        """Fetch token metadata from blockchain via contract calls"""
        try:
            checksum_address = self.web3.to_checksum_address(token_address)

            abi = self._get_abi_for_token_type(token_type)
            contract = self.web3.eth.contract(address=checksum_address, abi=abi)

            symbol = self._fetch_symbol(contract)
            name = self._fetch_name(contract)
            decimals = self._fetch_decimals(contract, token_type)

            result = (symbol, decimals)
            self._save_to_db(token_address, token_type, symbol, name, decimals, failed=False)

            return result

        except Exception as e:
            print(f"Could not fetch metadata for {token_address}: {e}")

            self._save_to_db(token_address, token_type, None, None, None, failed=True)
            return (None, None)

    def _get_abi_for_token_type(self, token_type: str) -> list:
        """Get minimal ABI for token type"""
        if token_type == "erc721":
            return [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "name",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function",
                },
            ]
        elif token_type == "erc1155":
            return [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "name",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function",
                }
            ]
        else:  # ERC20
            return [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "name",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function",
                },
            ]

    def _fetch_symbol(self, contract):
        """Fetch symbol from contract"""
        try:
            return contract.functions.symbol().call()
        except Exception:
            return None

    def _fetch_name(self, contract):
        """Fetch name from contract"""
        try:
            return contract.functions.name().call()
        except Exception:
            return None

    def _fetch_decimals(self, contract, token_type: str):
        """Fetch decimals from contract (only for ERC20)"""
        if token_type != "erc20":
            return None

        try:
            return contract.functions.decimals().call()
        except Exception:
            return None

    def _save_to_db(
        self,
        token_address: str,
        token_type: str,
        symbol: Optional[str],
        name: Optional[str],
        decimals: Optional[int],
        failed: bool = False,
    ):
        """Save token metadata to database"""
        session = SessionLocal()
        try:
            token = Token(
                token_address=token_address.lower(),
                token_type=token_type,
                symbol=symbol,
                name=name,
                decimals=decimals,
                failed=failed,
            )
            session.merge(token)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Warning: Could not save token to DB: {e}")
        finally:
            session.close()
