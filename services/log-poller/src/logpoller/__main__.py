import asyncio
from .logpoller import LogPoller



def main() -> None:
  print("Starting log poller")
  poller = LogPoller()

  async def run() -> None:
    async for log in poller.stream_new_logs():
      block_num = int(log.get("blockNumber", "0x0"), 16)
      tx_hash = log.get("transactionHash", "N/A")
      address = log.get("address", "N/A")
      

  asyncio.run(run())


if __name__ == "__main__":
  main()


