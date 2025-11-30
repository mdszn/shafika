import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock

# Add source directories to python path
# Assuming structure:
# /root
#   /libs/common/src
#   /services/log-processor/src
#   /services/block-processor/src
#   /tests

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir / "libs/common/src"))
sys.path.append(str(root_dir / "services/log-processor/src"))
sys.path.append(str(root_dir / "services/block-processor/src"))
sys.path.append(str(root_dir / "services/block-poller/src"))
sys.path.append(str(root_dir / "services/log-poller/src"))
sys.path.append(str(root_dir / "services/nft-metadata-worker/src"))
sys.path.append(str(root_dir / "services/api/src"))


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
