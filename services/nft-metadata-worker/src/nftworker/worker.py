import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from web3 import Web3
from common.db import SessionLocal
from common.nft import NftMetadataFetcher
from db.models.models import NftMetadata
from sqlalchemy import func


class NftMetadataWorker:
    """Background worker that fetches NFT metadata"""

    def __init__(self, batch_size: int = 50, delay_seconds: int = 5):
        load_dotenv()
        http_url = os.getenv("ETH_HTTP_URL")
        self.web3 = Web3(Web3.HTTPProvider(http_url))
        self.fetcher = NftMetadataFetcher(self.web3)
        self.batch_size = batch_size
        self.delay_seconds = delay_seconds

    def run(self):
        """Main loop: continuously fetch metadata for unfetched NFTs"""
        print("NFT Metadata Worker starting...")
        print(f"Batch size: {self.batch_size}, Delay: {self.delay_seconds}s")

        while True:
            try:
                session = SessionLocal()

                # Find NFTs without metadata
                unfetched_nfts = (
                    session.query(NftMetadata)
                    .filter(
                        NftMetadata.metadata_fetched == False,
                        NftMetadata.metadata_fetch_failed == False,
                    )
                    .limit(self.batch_size)
                    .all()
                )

                if unfetched_nfts:
                    print(
                        f"\nProcessing {len(unfetched_nfts)} NFTs without metadata..."
                    )

                    for nft in unfetched_nfts:
                        self._fetch_and_update_metadata(nft, session)

                    session.commit()
                    print(f"✅ Batch complete\n")
                else:
                    # Also retry failed fetches periodically (older than 1 day)
                    retry_nfts = (
                        session.query(NftMetadata)
                        .filter(
                            NftMetadata.metadata_fetch_failed == True,
                            NftMetadata.last_fetched_at
                            < datetime.now() - timedelta(days=1),
                        )
                        .limit(self.batch_size // 2)  # Retry fewer at a time
                        .all()
                    )

                    if retry_nfts:
                        print(f"\nRetrying {len(retry_nfts)} failed NFTs...")
                        for nft in retry_nfts:
                            self._fetch_and_update_metadata(nft, session)
                        session.commit()
                        print(f"✅ Retry batch complete\n")
                    else:
                        print("No NFTs to process. Sleeping...")

                session.close()
                time.sleep(self.delay_seconds)

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(self.delay_seconds)

    def _fetch_and_update_metadata(self, nft: NftMetadata, session):
        """Fetch metadata for a single NFT and update the record"""
        try:
            print(
                f"  Fetching {nft.token_address[:10]}...#{nft.token_id}"
            )

            # Step 1: Get tokenURI from contract (on-chain)
            token_uri = self.fetcher.get_token_uri(
                nft.token_address, nft.token_id
            )

            if token_uri:
                nft.token_uri = token_uri

                # Step 2: Fetch metadata from URI (off-chain)
                metadata = self.fetcher.fetch_metadata_from_uri(token_uri)

                if metadata:
                    # Parse and store metadata fields
                    nft.name = metadata.get("name")
                    nft.description = metadata.get("description")
                    nft.external_url = metadata.get("external_url")
                    nft.animation_url = metadata.get("animation_url")

                    # Normalize image URL (convert IPFS to gateway)
                    image_url = metadata.get("image")
                    if image_url:
                        nft.image_url = self.fetcher.normalize_image_url(image_url)

                    # Store attributes as JSON
                    attributes = metadata.get("attributes", [])
                    nft.attributes = attributes

                    # Mark as successfully fetched
                    nft.metadata_fetched = True
                    nft.metadata_fetch_failed = False
                    nft.metadata_fetch_error = None

                    print(f"    ✓ {nft.name or 'Unnamed'}")
                else:
                    # Failed to fetch metadata from URI
                    nft.metadata_fetch_failed = True
                    nft.metadata_fetch_error = "Failed to fetch metadata from URI"
                    print(f"    ✗ Failed to fetch metadata from URI")
            else:
                # Failed to get tokenURI
                nft.metadata_fetch_failed = True
                nft.metadata_fetch_error = "Failed to get tokenURI from contract"
                print(f"    ✗ Failed to get tokenURI")

        except Exception as e:
            nft.metadata_fetch_failed = True
            nft.metadata_fetch_error = str(e)[:500]  # Truncate long errors
            print(f"    ✗ Error: {e}")

        finally:
            nft.last_fetched_at = func.now()
            nft.updated_at = func.now()
