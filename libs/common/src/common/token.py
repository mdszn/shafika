from typing import Optional
from web3 import Web3
from .db import SessionLocal
from db.models.models import Token


class TokenMetadata:
  """Service for fetching and caching token metadata (symbol, decimals, etc.)"""
  
  def __init__(self, web3: Web3):
    self.web3 = web3
  
  def get_metadata(self, token_address: str, token_type: str = "erc20") -> tuple[Optional[str], Optional[int]]:
    """
    Get token symbol and decimals with 2-tier caching:
    1. Database cache (fast - uses PRIMARY KEY index)
    2. Blockchain call (slow - only if not in DB)
    
    Returns: (symbol, decimals)
    """
    token_address_lower = token_address.lower()
    session = SessionLocal()
    try:
      token = session.query(Token).filter(Token.token_address == token_address_lower).first()
      
      if token:
        return (token.symbol, token.decimals)
    finally:
      session.close()
    
    return self._fetch_from_blockchain(token_address_lower, token_type)
  
  def _fetch_from_blockchain(self, token_address: str, token_type: str) -> tuple[Optional[str], Optional[int]]:
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
      print(f"  Warning: Could not fetch metadata for {token_address}: {e}")
      
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
          "type": "function"
        },
        {
          "constant": True,
          "inputs": [],
          "name": "name",
          "outputs": [{"name": "", "type": "string"}],
          "type": "function"
        }
      ]
    elif token_type == "erc1155":
      return [
        {
          "constant": True,
          "inputs": [],
          "name": "name",
          "outputs": [{"name": "", "type": "string"}],
          "type": "function"
        }
      ]
    else:  # ERC20
      return [
        {
          "constant": True,
          "inputs": [],
          "name": "symbol",
          "outputs": [{"name": "", "type": "string"}],
          "type": "function"
        },
        {
          "constant": True,
          "inputs": [],
          "name": "decimals",
          "outputs": [{"name": "", "type": "uint8"}],
          "type": "function"
        },
        {
          "constant": True,
          "inputs": [],
          "name": "name",
          "outputs": [{"name": "", "type": "string"}],
          "type": "function" 
        }
      ]
  
  def _fetch_symbol(self, contract) -> Optional[str]:
    """Fetch symbol from contract"""
    try:
      return contract.functions.symbol().call()
    except Exception:
      return None
      
  def _fetch_name(self, contract) -> Optional[str]:
    """Fetch name from contract"""
    try:
      return contract.functions.name().call()
    except Exception:
      return None
  
  def _fetch_decimals(self, contract, token_type: str) -> Optional[int]:
    """Fetch decimals from contract (only for ERC20)"""
    if token_type != "erc20":
      return None
    
    try:
      return contract.functions.decimals().call()
    except Exception:
      return None
  
  def _save_to_db(self, token_address: str, token_type: str, symbol: Optional[str],
                   name: Optional[str], decimals: Optional[int], failed: bool = False):
    """Save token metadata to database"""
    session = SessionLocal()
    try:
      token = Token(
        token_address=token_address.lower(),
        token_type=token_type,
        symbol=symbol,
        name=name,
        decimals=decimals,
        failed=failed
      )
      session.merge(token)
      session.commit()
    except Exception as e:
      session.rollback()
      print(f"  Warning: Could not save token to DB: {e}")
    finally:
      session.close()

