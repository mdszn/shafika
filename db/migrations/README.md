# Database Migrations

This directory contains database migration files.

## Running Migrations

### Option 1: Using the migration script (Recommended)

```bash
cd scripts
python run_migration.py ../db/migrations/001_add_enums.sql
```

### Option 2: Using psql directly

```bash
psql -U your_username -d your_database -f db/migrations/001_add_enums.sql
```

### Option 3: Using the Python DB connection

```python
from common.db import execute_sql_file
execute_sql_file('db/migrations/001_add_enums.sql')
```

## Migration Files

### 001_add_enums.sql
Converts TEXT columns to PostgreSQL ENUM types:
- Creates `worker_status` ENUM: `processing`, `done`, `error`, `retrying`
- Creates `job_type` ENUM: `process_block`, `process_log`
- Alters `blocks.worker_status` to use `worker_status` ENUM
- Alters `failed_jobs.job_type` to use `job_type` ENUM
- Alters `failed_jobs.status` to use `worker_status` ENUM

## Important Notes

- Migrations are idempotent - you can run them multiple times safely
- The ENUM creation uses `DO $$ ... EXCEPTION` blocks to handle existing types
- Existing data will be preserved during column type conversion
- Make sure to backup your database before running migrations on production

## After Running Migration

Update your application code to use the ENUMs:

```python
from db.models.models import WorkerStatus, JobType

# Set status
block.worker_status = WorkerStatus.DONE

# Compare status
if job.status == WorkerStatus.ERROR:
    # handle error
```

