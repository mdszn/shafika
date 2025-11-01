from common.db import SessionLocal
from db.models.models import FailedJob

class FailedJobManager:
  queue_name: str
  job_type: str
  
  def __init__(self, queue_name: str, job_type: str):
    self.queue_name = queue_name
    self.job_type = job_type
    
  
  def record(self, job_id: str, data: dict, error: str):
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
      
  # TODO: Need to implement re-drive mechanism 