import pytest
from unittest.mock import MagicMock, patch
from common.nft import NftMetadataFetcher

VALID_CONTRACT = "0x0000000000000000000000000000000000000001"


@pytest.fixture
def nft_fetcher(mock_web3):
    return NftMetadataFetcher(mock_web3)


def test_get_token_uri_erc721(nft_fetcher, mock_web3):
    # Setup mock for ERC721 tokenURI
    contract_mock = MagicMock()
    mock_web3.eth.contract.return_value = contract_mock
    contract_mock.functions.tokenURI.return_value.call.return_value = "http://metadata"

    uri = nft_fetcher.get_token_uri(VALID_CONTRACT, 1)
    assert uri == "http://metadata"
    contract_mock.functions.tokenURI.assert_called_with(1)


def test_get_token_uri_erc1155_fallback(nft_fetcher, mock_web3):
    # Setup mock to fail ERC721 and succeed ERC1155
    contract_mock = MagicMock()
    mock_web3.eth.contract.return_value = contract_mock

    # First call raises exception
    contract_mock.functions.tokenURI.return_value.call.side_effect = Exception(
        "Not ERC721"
    )
    # Second call (uri) succeeds
    contract_mock.functions.uri.return_value.call.return_value = "http://metadata"

    uri = nft_fetcher.get_token_uri(VALID_CONTRACT, 1)
    assert uri == "http://metadata"
    contract_mock.functions.uri.assert_called_with(1)


@patch("requests.get")
def test_fetch_metadata_ipfs(mock_get, nft_fetcher):
    mock_get.return_value.json.return_value = {"name": "NFT"}

    metadata = nft_fetcher.fetch_metadata_from_uri("ipfs://QmHash")

    assert metadata == {"name": "NFT"}
    # Should try gateway
    assert "https://ipfs.io/ipfs/QmHash" in mock_get.call_args[0][0]


def test_normalize_image_url(nft_fetcher):
    assert nft_fetcher.normalize_image_url("http://img") == "http://img"
    assert (
        nft_fetcher.normalize_image_url("ipfs://QmHash")
        == "https://ipfs.io/ipfs/QmHash"
    )


@patch("common.nft.SessionLocal")
def test_create_nft_metadata(mock_session_local, nft_fetcher):
    session = mock_session_local.return_value
    session.query.return_value.filter.return_value.first.return_value = None

    nft_fetcher.create_nft_metadata(
        token_address=VALID_CONTRACT,
        token_id=1,
        owner="0xOwner",
        block_number=100,
        tx_hash="0xTx",
    )

    assert session.add.called
    nft = session.add.call_args[0][0]
    assert nft.token_address == VALID_CONTRACT
    assert nft.token_id == 1
    assert nft.owner == "0xOwner"
