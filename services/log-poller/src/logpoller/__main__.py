import asyncio
from .logpoller import LogPoller


def main() -> None:
    print("Starting log poller")
    poller = LogPoller()

    async def run() -> None:
        async for log in poller.stream_new_logs():
            address = log.get("address", "N/A")

    asyncio.run(run())


if __name__ == "__main__":
    main()
