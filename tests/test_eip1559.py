from unittest.mock import patch

import pytest
from blockprocessor.processor import BlockProcessor


@pytest.fixture
def block_processor(mock_web3, mock_redis):
    with (
        patch("blockprocessor.processor.load_dotenv"),
        patch("blockprocessor.processor.Web3"),
        patch("blockprocessor.processor.RedisQueueManager"),
        patch("blockprocessor.processor.TokenMetadata") as MockToken,
    ):

        processor = BlockProcessor("blocks")
        processor.web3 = mock_web3
        processor.redis_client = mock_redis
        processor.token = MockToken.return_value

        processor.token.get_eth_price.return_value = 2000.0

        def from_wei(value, unit):
            return float(value) / 10**18

        processor.web3.from_wei = from_wei

        return processor


def test_parse_legacy_transaction(block_processor):
    """Test parsing a Type 0 (Legacy) transaction."""
    tx_data = {
        "hash": b"0xLegacyHash",
        "from": "0xSender",
        "to": "0xReceiver",
        "value": 1000000000000000000,  # 1 ETH
        "gas": 21000,
        "gasPrice": 50000000000,  # 50 gwei
        "type": 0,  # Legacy
        "input": "0x",
    }

    # Base fee shouldn't matter for legacy effective gas price (it's just gasPrice)
    base_fee = 40000000000  # 40 gwei

    tx = block_processor._parse_transaction(
        tx_data,
        block_number=100,
        block_hash="0xBlockHash",
        block_ts=1234567890,
        base_fee_per_gas=base_fee,
    )

    assert tx.txn_type == 0
    assert tx.gas_price == 50000000000
    assert tx.effective_gas_price == 50000000000  # Should equal gasPrice
    assert tx.max_fee_per_gas is None
    assert tx.max_priority_fee_per_gas is None


def test_parse_eip1559_transaction_high_fee(block_processor):
    """
    Test EIP-1559 where BaseFee + Tip < MaxFee.
    Effective Gas Price = BaseFee + Tip
    """
    base_fee = 100  # gwei (simplified)
    max_priority = 5  # Tip
    max_fee = 200  # Cap

    tx_data = {
        "hash": b"0xEIP1559Hash",
        "from": "0xSender",
        "to": "0xReceiver",
        "value": 0,
        "gas": 21000,
        "gasPrice": 105,  # Usually nodes populate this with effective price, but we calculate it
        "type": 2,  # EIP-1559
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority,
        "input": "0x",
    }

    tx = block_processor._parse_transaction(
        tx_data,
        block_number=100,
        block_hash="0xBlockHash",
        block_ts=1234567890,
        base_fee_per_gas=base_fee,
    )

    assert tx.txn_type == 2
    assert tx.max_fee_per_gas == max_fee
    assert tx.max_priority_fee_per_gas == max_priority

    expected_effective = base_fee + max_priority
    assert tx.effective_gas_price == expected_effective


def test_parse_eip1559_transaction_capped(block_processor):
    """
    Test EIP-1559 where BaseFee + Tip > MaxFee.
    Effective Gas Price = MaxFee (Capped)
    """
    base_fee = 150  # High base fee
    max_priority = 10
    max_fee = 120  # Low cap (user didn't predict base fee spike)

    tx_data = {
        "hash": b"0xEIP1559Hash",
        "from": "0xSender",
        "to": "0xReceiver",
        "value": 0,
        "gas": 21000,
        "gasPrice": max_fee,
        "type": 2,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority,
        "input": "0x",
    }

    tx = block_processor._parse_transaction(
        tx_data,
        block_number=100,
        block_hash="0xBlockHash",
        block_ts=1234567890,
        base_fee_per_gas=base_fee,
    )

    assert tx.txn_type == 2

    # Calculation: min(120, 150 + 10) = 120
    # User pays their max cap, even though it's not enough for the full tip
    # (In reality, this tx might not be mined if base_fee > max_fee, but if it was included, this is the math)
    assert tx.effective_gas_price == max_fee


def test_parse_eip1559_no_base_fee(block_processor):
    """Test handling when base_fee_per_gas is missing (e.g. older block processed with new code)."""
    tx_data = {
        "hash": b"0xEIP1559Hash",
        "type": 2,
        "maxFeePerGas": 200,
        "maxPriorityFeePerGas": 5,
        "gasPrice": 105,
        "input": "0x",
    }

    tx = block_processor._parse_transaction(
        tx_data, 100, "0xHash", 12345, base_fee_per_gas=None  # Missing
    )

    assert tx.effective_gas_price == 105
