import redis
import json

class RedisQueueManager:
  client: redis.Redis

  """Manages a Redis-backed queue."""
  def __init__(self, host='localhost', port=6379, db=0):
    self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

  def push(self, queue_name: str, item: str):
    self.client.rpush(queue_name, item)
    
  def push_json(self, queue_name: str, data: dict):
    """Push a JSON object to the queue."""
    self.client.rpush(queue_name, json.dumps(data))

  def blocking_pop(self, queue_name: str, timeout: int = 0):
    result = self.client.blpop(queue_name, timeout=timeout)
    if result:
      _, item = result
      return item
    return None

  def pop_json(self, queue_name: str):
    """Pop and parse JSON from queue."""
    item = self.client.lpop(queue_name)
    return json.loads(item) if item else None

  def blocking_pop_json(self, queue_name: str, timeout: int = 0):
    """Block until JSON object is available."""
    result = self.client.blpop(queue_name, timeout=timeout)
    if result:
      _, item = result
      return json.loads(item)
    return None

