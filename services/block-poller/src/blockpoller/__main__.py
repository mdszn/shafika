import asyncio
from .blockpoller import BlockPoller


def main() -> None:
    try:
        poller = BlockPoller()
        print(f"Redis connected")
    except Exception as e:
        print(f"FATAL ERROR during initialization: {e}")
        raise

    async def run() -> None:
        async for head in poller.stream_new_block():
            block_num = int(head["number"], 16)
            print(f"Block #{block_num}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
