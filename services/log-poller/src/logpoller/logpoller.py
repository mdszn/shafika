import os
import asyncio
import json
from websockets import connect
from dotenv import load_dotenv
from common.queue import RedisQueueManager

class LogPoller:
  http_url: str
  ws_url: str
  queue: RedisQueueManager
  queue_name: str
  
  def __init__(self, queue_name: str = "logs"):
    load_dotenv()
    self.http_url = os.getenv("ETH_HTTP_URL")
    self.ws_url = os.getenv("ETH_WS_URL")
    self.queue = RedisQueueManager()
    self.queue_name = queue_name
    
  async def stream_new_logs(self):
    """Stream all transaction logs from Ethereum blockchain via WebSocket subscription"""
    while True:
      try:
        async with connect(self.ws_url) as ws:
          print(f"Connected to WebSocket: {self.ws_url}")
          
          subscription_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["logs", {}]
          }
          
          await ws.send(json.dumps(subscription_request))
          subscription_response = await ws.recv()
          sub_data = json.loads(subscription_response)
          
          if "error" in sub_data:
            error = sub_data["error"]
            raise Exception(f"Subscription error: {error}")
          
          while True:
            message = await asyncio.wait_for(ws.recv(), timeout=60)
            payload = json.loads(message)
            
            log_event = payload.get("params", {}).get("result")
            
            if log_event:
              block_number_hex = log_event.get("blockNumber")
              if block_number_hex:
                address = log_event.get("address")
                block_number = int(block_number_hex, 16)
                block_hash = log_event.get("blockHash")
                block_timestamp = log_event.get("blockTimestamp")
                data = log_event.get("data")
                log_index = log_event.get("logIndex", "0x0")
                topics = log_event.get("topics", [])
                transaction_hash = log_event.get("transactionHash")
                transaction_index = log_event.get("transactionIndex")
                
                
                job = {
                  "job_type": "process_log",
                  "address": address,
                  "block_number": block_number,
                  "block_hash": block_hash,
                  "block_timestamp": block_timestamp,
                  "data": data,
                  "log_index": log_index,
                  "topics": topics,
                  "transaction_hash": transaction_hash,
                  "transaction_index": transaction_index
                }
                self.queue.push_json(self.queue_name, job)
              
              yield log_event
      except Exception as e:
        print(f"Error in log streaming: {e}")
        await asyncio.sleep(2)
    