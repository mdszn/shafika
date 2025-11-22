from .worker import NftMetadataWorker


def main() -> None:
    print("Starting NFT metadata worker...")
    worker = NftMetadataWorker(batch_size=50, delay_seconds=5)
    worker.run()


if __name__ == "__main__":
    main()
