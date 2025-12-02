from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_web3():
    mock = MagicMock()
    mock.eth.contract = MagicMock()
    mock.to_checksum_address = lambda x: x
    return mock


@pytest.fixture
def mock_redis():
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_db_session():
    mock = MagicMock()
    return mock
