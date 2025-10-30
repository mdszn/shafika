import asyncio
from .blockpoller import BlockPoller



def main() -> None:
  print("Starting block processor")
  poller = BlockPoller()

  async def run() -> None:
    async for head in poller.stream_new_block():
      print(int(head["number"], 16))

  asyncio.run(run())


if __name__ == "__main__":
  main()


