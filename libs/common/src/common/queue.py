import redis
import json

class RedisQueueManager:
  client: redis.Redis

  """Manages a Redis-backed queue."""
  def __init__(self, host='localhost', port=6379, db=0):
    self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

  def push(self, queue_name: str, item: str):
    self.client.rpush(queue_name, item)
    
  def push_json(self, queue_name: str, job_id: str, data: dict):
    """Push job ID to queue and store data."""
    self.client.set(job_id, json.dumps(data))
    self.client.rpush(queue_name, job_id)

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
    """Pop job ID from queue and fetch its data."""
    result = self.client.blpop(queue_name, timeout=timeout)
    if not result:
      return None, None
   
    _, job_id = result
    job_data = self.client.get(job_id)
    return job_id, json.loads(job_data)

  def delete_job(self, job_id: str):
    """Delete job data after processing."""
    self.client.delete(job_id)

