import asyncio

from .logpoller import LogPoller


def main() -> None:
    print("Starting log poller")
    poller = LogPoller()

    async def run() -> None:
        async for log in poller.stream_new_logs():
            pass  # Just consume the logs

    asyncio.run(run())


if __name__ == "__main__":
    main()
