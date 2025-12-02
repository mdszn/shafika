import asyncio
import json
import os

from common.queue import RedisQueueManager
from dotenv import load_dotenv
from websockets import connect

from db.models.models import BlockJob, JobType


class BlockPoller:
    http_url: str
    ws_url: str
    redis_client: RedisQueueManager
    queue_name: str

    def __init__(self, queue_name: str = "blocks"):
        load_dotenv()
        ws_url = os.getenv("ETH_WS_URL")
        http_url = os.getenv("ETH_HTTP_URL")

        if not ws_url:
            raise ValueError("ETH_WS_URL not set in environment")
        if not http_url:
            raise ValueError("ETH_HTTP_URL not set in environment")

        self.ws_url = ws_url
        self.http_url = http_url
        self.redis_client = RedisQueueManager()
        self.queue_name = queue_name

    async def stream_new_block(self):
        print("Starting block poller")
        while True:
            try:
                async with connect(self.ws_url) as ws:
                    print("Connected to Ethereum node")
                    await ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "eth_subscribe",
                                "params": ["newHeads"],
                            }
                        )
                    )
                    subscription_response = await ws.recv()
                    print(f"Subscribed to newHeads: {subscription_response}")

                    while True:
                        message = await asyncio.wait_for(ws.recv(), timeout=60)
                        payload = json.loads(message)
                        header = payload.get("params", {}).get("result")
                        if header:
                            block_number_hex = header.get("number")
                            if block_number_hex:
                                block_number = int(block_number_hex, 16)
                                block_hash = header.get("hash")
                                print(f"New block {block_number} - pushing to queue")
                                job_id = f"block:{block_number}"
                                job_data: BlockJob = {
                                    "job_type": JobType.BLOCK.value,
                                    "block_number": block_number,
                                    "block_hash": block_hash,
                                    "status": "new",
                                }
                                self.redis_client.push_json(
                                    self.queue_name, job_id, job_data
                                )
                            yield header
            except Exception as e:
                print(f"ERROR: {type(e).__name__}: {e}")
                print("Reconnecting in 2 seconds...")
                await asyncio.sleep(2)
