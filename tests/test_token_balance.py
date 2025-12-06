from unittest.mock import MagicMock, patch
import pytest
from logprocessor.logprocessor import LogProcessor


@pytest.fixture
def log_processor(mock_web3, mock_redis):
    with (
        patch("logprocessor.logprocessor.load_dotenv"),
        patch("logprocessor.logprocessor.Web3"),
        patch("logprocessor.logprocessor.RedisQueueManager"),
        patch("logprocessor.logprocessor.TokenMetadata"),
        patch("logprocessor.logprocessor.DexProcessor"),
        patch("logprocessor.logprocessor.NftMetadataFetcher"),
    ):

        processor = LogProcessor("logs")
        processor.web3 = mock_web3
        return processor


@patch("logprocessor.logprocessor.SessionLocal")
def test_update_balance_insert(mock_session_local, log_processor):
    """Test inserting a new balance record."""
    session = mock_session_local.return_value

    # Mock data
    address = "0xUser"
    token = "0xToken"
    amount = 100

    log_processor._update_balance(session, address, token, 0, "erc20", amount)

    assert session.execute.called


@patch("logprocessor.logprocessor.SessionLocal")
def test_save_transfer_updates_balances(mock_session_local, log_processor):
    """Test that saving a transfer updates both sender and receiver balances."""
    log_processor._update_balance = MagicMock()

    # Test Data
    kwargs = {
        "from_address": "0xSender",
        "to_address": "0xReceiver",
        "token_address": "0xToken",
        "amount": 50,
        "token_type": "erc20",
        "block_number": 100,
        "tx_hash": "0xTx",
        "log_index": 1,
    }

    log_processor._save_transfer(**kwargs)

    assert log_processor._update_balance.call_count == 2

    call_sender = log_processor._update_balance.call_args_list[0]
    assert call_sender[0][1] == "0xSender"
    assert call_sender[0][5] == -50  # Negative amount

    call_receiver = log_processor._update_balance.call_args_list[1]
    assert call_receiver[0][1] == "0xReceiver"
    assert call_receiver[0][5] == 50


@patch("logprocessor.logprocessor.SessionLocal")
def test_save_transfer_zero_address_ignored(mock_session_local, log_processor):
    """Test that minting (from zero address) or burning (to zero address) skips balance update for zero addr."""
    log_processor._update_balance = MagicMock()

    zero_addr = "0x0000000000000000000000000000000000000000"
    kwargs = {
        "from_address": zero_addr,
        "to_address": "0xUser",
        "token_address": "0xToken",
        "amount": 100,
        "token_type": "erc20",
    }

    log_processor._save_transfer(**kwargs)

    assert log_processor._update_balance.call_count == 1
    assert log_processor._update_balance.call_args[0][1] == "0xUser"
