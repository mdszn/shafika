import pytest
from unittest.mock import MagicMock, patch
from common.dex import (
    DexProcessor,
    UNISWAP_V2_SWAP_SIGNATURE,
    UNISWAP_V3_SWAP_SIGNATURE,
    UNISWAP_V2_FACTORY,
)

# Sample data
VALID_POOL = "0x0000000000000000000000000000000000000001"
VALID_TOKEN0 = "0x0000000000000000000000000000000000000002"
VALID_TOKEN1 = "0x0000000000000000000000000000000000000003"

LOG_JOB_V2 = {
    "address": VALID_POOL,
    "topics": [
        UNISWAP_V2_SWAP_SIGNATURE,
        "0x0000000000000000000000000000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000000000000000000000000000002",
    ],
    "data": "0x" + "00" * 32 + "00" * 31 + "01" + "00" * 32 + "00" * 31 + "02",
    # amount0In=0, amount1In=1, amount0Out=0, amount1Out=2
    "transaction_hash": "0xTxHash",
    "log_index": "0x1",
    "block_number": 100,
    "block_timestamp": "0x1234567890",
    "transaction_index": "0x1",
}

# Encode V3 data safely
# amount0 = -100 (in), amount1 = 200 (out)
amount0_bytes = (-100).to_bytes(32, byteorder="big", signed=True)
amount1_bytes = (200).to_bytes(32, byteorder="big", signed=True)
sqrt_price_bytes = (0).to_bytes(32, byteorder="big", signed=False)
liquidity_bytes = (0).to_bytes(32, byteorder="big", signed=False)
tick_bytes = (0).to_bytes(32, byteorder="big", signed=True)

data_bytes = (
    amount0_bytes + amount1_bytes + sqrt_price_bytes + liquidity_bytes + tick_bytes
)
v3_data_hex = "0x" + data_bytes.hex()

LOG_JOB_V3 = {
    "address": VALID_POOL,
    "topics": [
        UNISWAP_V3_SWAP_SIGNATURE,
        "0x0000000000000000000000000000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000000000000000000000000000002",
    ],
    "data": v3_data_hex,
    "transaction_hash": "0xTxHash",
    "log_index": "0x1",
    "block_number": 100,
    "block_timestamp": "0x1234567890",
    "transaction_index": "0x1",
}


@pytest.fixture
def dex_processor(mock_web3):
    return DexProcessor(mock_web3)


@patch("common.dex.SessionLocal")
def test_process_uniswap_v2_swap(mock_session_local, dex_processor, mock_web3):
    # Setup mocks
    session = mock_session_local.return_value
    mock_web3.eth.contract.return_value.functions.token0.return_value.call.return_value = (
        VALID_TOKEN0
    )
    mock_web3.eth.contract.return_value.functions.token1.return_value.call.return_value = (
        VALID_TOKEN1
    )
    # Mock factory call to return Uniswap V2 factory
    mock_web3.eth.contract.return_value.functions.factory.return_value.call.return_value = (
        UNISWAP_V2_FACTORY
    )

    # Run
    dex_processor.process_uniswap_v2_swap(LOG_JOB_V2, LOG_JOB_V2["topics"])

    # Assertions
    assert session.add.called
    assert session.commit.called

    # Check the Swap object passed to session.add
    swap = session.add.call_args[0][0]
    assert swap.dex_name == "uniswap_v2"
    assert swap.pool_address == VALID_POOL.lower()
    assert swap.amount1_in == "1"
    assert swap.amount1_out == "2"


@patch("common.dex.SessionLocal")
def test_process_uniswap_v3_swap(mock_session_local, dex_processor, mock_web3):
    # Setup mocks
    session = mock_session_local.return_value
    mock_web3.eth.contract.return_value.functions.token0.return_value.call.return_value = (
        VALID_TOKEN0
    )
    mock_web3.eth.contract.return_value.functions.token1.return_value.call.return_value = (
        VALID_TOKEN1
    )

    # Run
    dex_processor.process_uniswap_v3_swap(LOG_JOB_V3, LOG_JOB_V3["topics"])

    # Assertions
    assert session.add.called
    assert session.commit.called

    swap = session.add.call_args[0][0]
    assert swap.dex_name == "uniswap_v3"
    assert swap.pool_address == VALID_POOL.lower()
    # amount0 = -100 -> amount0_in = 100
    assert swap.amount0_in == "100"
    assert swap.amount0_out == "0"
    # amount1 = 200 -> amount1_out = 200
    assert swap.amount1_in == "0"
    assert swap.amount1_out == "200"


def test_get_pool_tokens_caching(dex_processor, mock_web3):
    # Setup mock
    mock_web3.eth.contract.return_value.functions.token0.return_value.call.return_value = (
        VALID_TOKEN0
    )
    mock_web3.eth.contract.return_value.functions.token1.return_value.call.return_value = (
        VALID_TOKEN1
    )

    # First call
    t0, t1 = dex_processor._get_pool_tokens(VALID_POOL)
    assert t0 == VALID_TOKEN0
    assert t1 == VALID_TOKEN1
    assert mock_web3.eth.contract.called

    # Reset mock
    mock_web3.eth.contract.reset_mock()

    # Second call (should be cached)
    t0, t1 = dex_processor._get_pool_tokens(VALID_POOL)
    assert t0 == VALID_TOKEN0
    assert t1 == VALID_TOKEN1
    assert not mock_web3.eth.contract.called
