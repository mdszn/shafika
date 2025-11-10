import redis
import json
from db.models.models import LogJob, BlockJob


class RedisQueueManager:
    client: redis.Redis

    """Manages a Redis-backed queue."""

    def __init__(self, host="localhost", port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def push_json(self, queue_name: str, job_id: str, data: LogJob | BlockJob):
        """Push job ID to queue and store data."""
        self.client.set(job_id, json.dumps(data))
        self.client.rpush(queue_name, job_id)
    
    def bl_pop_log(self, queue_name: str = "logs", timeout: int = 0) -> tuple[str | None, LogJob | None]:
        result = self.client.blpop([queue_name], timeout=timeout)
        if not result:
            return None, None

        _, job_id = result  # pyright: ignore
        job_data = self.client.get(job_id)
        return job_id, json.loads(job_data)  # pyright: ignore
    
    
    def bl_pop_block(self, queue_name: str = "logs", timeout: int = 0) -> tuple[str | None, BlockJob | None]:
        result = self.client.blpop([queue_name], timeout=timeout)
        if not result:
            return None, None

        _, job_id = result  # pyright: ignore
        job_data = self.client.get(job_id)
        return job_id, json.loads(job_data)  # pyright: ignore

    def delete_job(self, job_id: str):
        """Delete job data after processing."""
        self.client.delete(job_id)
