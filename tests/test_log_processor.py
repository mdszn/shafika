import pytest
from unittest.mock import MagicMock, patch, call
from logprocessor.logprocessor import (
    LogProcessor,
    UNISWAP_V2_SWAP_SIGNATURE,
    TRANSFER_EVENT_SIGNATURE,
    AddressStats,
)


@pytest.fixture
def log_processor(mock_web3):
    return LogProcessor()


@patch("logprocessor.logprocessor.SessionLocal")
def test_process_log_delegates_dex(mock_session, log_processor):
    log_processor.dex_processor = MagicMock()

    job = {"topics": [UNISWAP_V2_SWAP_SIGNATURE, "0xSender", "0xRecipient"]}

    log_processor.process_log(job)

    log_processor.dex_processor.process_uniswap_v2_swap.assert_called_once_with(
        job, job["topics"]
    )


@patch("logprocessor.logprocessor.SessionLocal")
def test_save_transfer_deadlock_prevention(mock_session_local, log_processor):
    """Test that address updates are sorted to prevent deadlocks"""
    session = mock_session_local.return_value

    # We mock _update_token_transfer_stats to track call order
    log_processor._update_token_transfer_stats = MagicMock()

    # Scenario: Transfer from Address B to Address A
    # (Lexicographically "0xAddressA" < "0xAddressB")
    addr_a = "0x000000000000000000000000000000000000000a"
    addr_b = "0x000000000000000000000000000000000000000b"

    kwargs = {
        "from_address": addr_b,
        "to_address": addr_a,
        "block_number": 100,
        "amount": 10,
        "token_address": "0xToken",
    }

    log_processor._save_transfer(**kwargs)

    # Check calls to _update_token_transfer_stats
    calls = log_processor._update_token_transfer_stats.call_args_list
    assert len(calls) == 2

    # First call should be for addr_a (smaller), even though it's the receiver
    args1 = calls[0][0]
    assert args1[1] == addr_a  # address arg

    # Second call should be for addr_b (larger)
    args2 = calls[1][0]
    assert args2[1] == addr_b


@patch("logprocessor.logprocessor.SessionLocal")
def test_process_erc20_transfer(mock_session_local, log_processor):
    session = mock_session_local.return_value
    log_processor.token_service.get_metadata = MagicMock(return_value=("SYM", 18))

    job = {
        "address": "0xToken",
        "transaction_hash": "0xTx",
        "log_index": "0x1",
        "block_number": 100,
        "block_timestamp": "0x12345",
        "data": "0x" + "00" * 31 + "0a",  # amount = 10
        "topics": [
            TRANSFER_EVENT_SIGNATURE,
            "0x0000000000000000000000000000000000000001",  # From
            "0x0000000000000000000000000000000000000002",  # To
        ],
    }

    log_processor.process_log(job)

    assert session.add.called
    transfer = session.add.call_args[0][0]
    assert transfer.amount == 10
    assert transfer.from_address == "0x0000000000000000000000000000000000000001"
    assert transfer.to_address == "0x0000000000000000000000000000000000000002"
