import pytest
from unittest.mock import MagicMock, patch
from blockprocessor.processor import BlockProcessor


@pytest.fixture
def block_processor(mock_web3, mock_redis):
    mock_web3.eth.get_block.return_value = {
        "hash": b"0xHash",
        "number": 100,
        "timestamp": 1234567890,
        "parentHash": b"0xParent",
        "transactions": [],
    }
    return BlockProcessor(queue_name="blocks")


@patch("blockprocessor.processor.SessionLocal")
def test_process_block_success(mock_session_local, block_processor):
    session = mock_session_local.return_value

    # process_block(block_number, block_hash, block_status)
    block_processor.process_block(100, "0xBlockHash", "new")

    assert session.add.called
    assert session.commit.called
    block = session.add.call_args[0][0]
    assert block.block_number == 100
    assert block.block_hash == "0xBlockHash"


@patch("blockprocessor.processor.SessionLocal")
def test_parse_transaction_value(mock_session_local, block_processor, mock_web3):
    # Setup ETH price mock on the TokenMetadata instance
    block_processor.token.get_eth_price = MagicMock(return_value=2000.0)
    mock_web3.from_wei.return_value = 1.5  # 1.5 ETH

    tx_data = {
        "hash": b"0xTxHash",
        "from": "0xSender",
        "to": "0xReceiver",
        "value": 1500000000000000000,  # 1.5 ETH in wei
        "gas": 21000,
        "gasPrice": 100,
        "input": "0x",
    }

    tx = block_processor._parse_transaction(tx_data, 100, "0xBlockHash", 12345)

    assert tx.value == 1500000000000000000
    assert tx.value_usd == 1.5 * 2000.0  # 3000.0


@patch("blockprocessor.processor.SessionLocal")
def test_parse_transaction_missing_fields(mock_session_local, block_processor):
    # Mock get_eth_price to avoid Redis connection
    block_processor.token.get_eth_price = MagicMock(return_value=2000.0)

    # Test handling of missing 'value' (TypedDict optional issue we fixed)
    tx_data = {
        "hash": b"0xTxHash",
        # Missing 'value', 'from', 'to'
    }

    tx = block_processor._parse_transaction(tx_data, 100, "0xBlockHash", 12345)

    assert tx.value == 0  # Should default to 0
    assert tx.from_address is None
