import os
import asyncio
import json
from websockets import connect
from dotenv import load_dotenv
from common.queue import RedisQueueManager

class BlockPoller:
  http_url: str
  ws_url: str
  queue: RedisQueueManager
  queue_name: str
  
  def __init__(self, queue_name: str = "blocks"):
    load_dotenv()
    self.http_url = os.getenv("ETH_HTTP_URL")
    self.ws_url = os.getenv("ETH_WS_URL")
    self.queue = RedisQueueManager()
    self.queue_name = queue_name
    
  async def stream_new_block(self):
    while True:
      try:
        async with connect(self.ws_url) as ws:
          await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}))
          await ws.recv()
          while True:
            message = await asyncio.wait_for(ws.recv(), timeout=60)
            payload = json.loads(message)
            header = payload.get("params", {}).get("result")
            if header:
              block_number_hex = header.get("number")
              if block_number_hex:
                block_number = int(block_number_hex, 16)
                block_hash = header.get("hash")
                print(f"Pushing block {block_number} into queue")
                job_id = f"block:{block_number}"
                job_data = {
                  "block_number": block_number,
                  "block_hash": block_hash
                }
                self.queue.push_json(self.queue_name, job_id, job_data)
              yield header 
      except Exception:
        await asyncio.sleep(2)
    