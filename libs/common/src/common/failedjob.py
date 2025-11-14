from common.db import SessionLocal
from db.models.models import FailedJob, LogJob, BlockJob, JobType, WorkerStatus
from sqlalchemy import select
from common.queue import RedisQueueManager
from datetime import datetime
from typing import cast


class FailedJobManager:
    queue_name: str
    job_type: JobType
    redis_client: RedisQueueManager

    def __init__(self, queue_name: str, job_type: JobType):
        self.queue_name = queue_name
        self.job_type = job_type
        self.redis_client = RedisQueueManager()

    def record(self, job_id: str, data: LogJob | BlockJob, error: str):
        """Saves failed job to failed_jobs table."""
        session = SessionLocal()
        failed_job = None

        try:
            failed_job = FailedJob(
                job_id=job_id,
                queue_name=self.queue_name,
                job_type=self.job_type,
                data=data,
                error=error,
            )

            session.add(failed_job)
            session.commit()
            return True

        except Exception as e:
            print(f"Failed trying to add {job_id} to failed_jobs table: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def redrive_failed_blocks(self):
        session = SessionLocal()

        try:
            failed_jobs = session.scalars(
                select(FailedJob).where(
                    (FailedJob.status == WorkerStatus.ERROR)
                    & (FailedJob.job_type == JobType.BLOCK)
                )
            ).all()

            for job in failed_jobs:
                job_data = cast(BlockJob, job.data)
                self.redis_client.push_json("blocks", job.job_id, job_data)  # pyright: ignore
                job.status = WorkerStatus.RETRYING  # pyright: ignore
                job.retries += 1  # pyright: ignore
                job.last_retry_at = datetime.now()  # pyright: ignore

            print(f"Push {len(failed_jobs)} jobs to 'blocks' queue for retry.")
            session.commit()
            return True

        except Exception as e:
            print(f"Failed trying to redrive failed jobs: {e}")
            session.rollback()
            return False
        finally:
            session.close()
