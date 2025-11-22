import requests
import base64
import json
from typing import Optional, Dict
from web3 import Web3


class NftMetadataFetcher:
    """Utility class for fetching NFT metadata"""

    # Multiple IPFS gateways for redundancy
    IPFS_GATEWAYS = [
        "https://ipfs.io/ipfs/",
        "https://cloudflare-ipfs.com/ipfs/",
        "https://gateway.pinata.cloud/ipfs/",
    ]

    def __init__(self, web3: Web3):
        self.web3 = web3

    def get_token_uri(self, contract_address: str, token_id: int) -> Optional[str]:
        """
        Fetch tokenURI from NFT contract (on-chain call)
        Supports both ERC721 and ERC1155
        """
        # Convert to int in case it's a Decimal from database
        token_id_int = int(token_id)

        try:
            # Try ERC721 tokenURI first
            erc721_abi = [
                {
                    "inputs": [{"name": "tokenId", "type": "uint256"}],
                    "name": "tokenURI",
                    "outputs": [{"name": "", "type": "string"}],
                    "stateMutability": "view",
                    "type": "function",
                }
            ]

            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(contract_address), abi=erc721_abi
            )
            token_uri = contract.functions.tokenURI(token_id_int).call()
            return token_uri

        except Exception as e:
            # Try ERC1155 uri as fallback
            try:
                erc1155_abi = [
                    {
                        "inputs": [{"name": "_id", "type": "uint256"}],
                        "name": "uri",
                        "outputs": [{"name": "", "type": "string"}],
                        "stateMutability": "view",
                        "type": "function",
                    }
                ]

                contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(contract_address), abi=erc1155_abi
                )
                token_uri = contract.functions.uri(token_id_int).call()
                return token_uri

            except Exception as e2:
                print(
                    f"Error fetching tokenURI for {contract_address}#{token_id}: {e}, {e2}"
                )
                return None

    def fetch_metadata_from_uri(self, token_uri: str) -> Optional[Dict]:
        """Fetch JSON metadata from tokenURI"""
        if not token_uri:
            return None

        try:
            # Handle IPFS URIs
            if token_uri.startswith("ipfs://"):
                ipfs_hash = token_uri.replace("ipfs://", "")
                return self._fetch_from_ipfs(ipfs_hash)

            # Handle data URIs (base64 encoded)
            elif token_uri.startswith("data:application/json"):
                return self._parse_data_uri(token_uri)

            # Handle HTTP(S) URIs
            elif token_uri.startswith("http://") or token_uri.startswith("https://"):
                return self._fetch_from_http(token_uri)

            else:
                print(f"Unknown URI scheme: {token_uri}")
                return None

        except Exception as e:
            print(f"Error fetching metadata from {token_uri}: {e}")
            return None

    def _fetch_from_ipfs(self, ipfs_hash: str) -> Optional[Dict]:
        """Try multiple IPFS gateways"""
        for gateway in self.IPFS_GATEWAYS:
            try:
                url = f"{gateway}{ipfs_hash}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                continue  # Try next gateway

        print(f"Failed to fetch from all IPFS gateways for {ipfs_hash}")
        return None

    def _fetch_from_http(self, url: str) -> Optional[Dict]:
        """Fetch from HTTP(S) URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching from HTTP: {e}")
            return None

    def _parse_data_uri(self, data_uri: str) -> Optional[Dict]:
        """Parse base64 encoded data URI"""
        try:
            # Format: data:application/json;base64,<data>
            if ";base64," in data_uri:
                json_data = data_uri.split(",", 1)[1]
                decoded = base64.b64decode(json_data)
                return json.loads(decoded)
            else:
                # Plain JSON without base64
                json_data = data_uri.split(",", 1)[1]
                return json.loads(json_data)
        except Exception as e:
            print(f"Error parsing data URI: {e}")
            return None

    def normalize_image_url(self, image_url: str) -> str:
        """Convert IPFS image URLs to gateway URLs"""
        if not image_url:
            return image_url

        if image_url.startswith("ipfs://"):
            ipfs_hash = image_url.replace("ipfs://", "")
            return f"{self.IPFS_GATEWAYS[0]}{ipfs_hash}"

        return image_url
