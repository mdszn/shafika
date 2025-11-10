# Quick Start: Running Migrations with Alembic

## Setup (One Time)

### 1. Install Alembic

```bash
# From project root
cd libs/common
pip install -e .
```

This installs alembic (now added to dependencies) along with other common lib dependencies.

### 2. Verify Installation

```bash
alembic --version
```

## Running Your ENUM Migration

### Step 1: Check Current Database State

```bash
# See what revision the database is at
alembic current
```

If it shows nothing, your database hasn't been stamped yet.

### Step 2: Generate Migration for ENUM Changes

```bash
# From project root (/Users/md/shafika)
alembic revision --autogenerate -m "add worker_status and job_type enums"
```

This will:
- Compare your SQLAlchemy models with the current database
- Create a new migration file in `alembic/versions/`
- Include changes for ENUM types

### Step 3: Review the Generated Migration

Open the newly created file in `alembic/versions/` and review it. It should contain:
- CREATE TYPE statements for `worker_status` and `job_type`
- ALTER TABLE statements to change column types

Example of what you'll see:
```python
def upgrade():
    # Create enum types
    sa.Enum('processing', 'done', 'error', 'retrying', name='workerstatus').create(op.get_bind())
    sa.Enum('process_block', 'process_log', name='jobtype').create(op.get_bind())
    
    # Alter columns
    op.alter_column('blocks', 'worker_status',
                    type_=sa.Enum('processing', 'done', 'error', 'retrying', name='workerstatus'))
    # ... more changes
```

### Step 4: Apply the Migration

```bash
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> abc123def456, add worker_status and job_type enums
```

### Step 5: Verify in Database

```bash
# Connect to your database
psql -U your_user -d your_db

# List enum types
\dT

# Should show:
#  worker_status | enum | ...
#  job_type      | enum | ...

# Check table structure
\d blocks
\d failed_jobs
```

## Common Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## If Things Go Wrong

### "Can't locate revision"
Your database has a version that doesn't exist in code:
```bash
alembic stamp base  # Reset
alembic upgrade head  # Reapply
```

### "Target database is not up to date"
```bash
alembic stamp head  # Mark database as current
```

### Import errors
Make sure you're in project root and virtual environment is activated:
```bash
cd /Users/md/shafika
source bin/activate  # or your venv activation
```

## After Migration Success

Your database will now have proper ENUM types, and you can use them in code:

```python
from db.models.models import WorkerStatus, JobType

# Set values
block.worker_status = WorkerStatus.DONE
job.job_type = JobType.BLOCK

# Compare
if job.status == WorkerStatus.ERROR:
    handle_error()
```

## Next Steps

After your ENUM migration works:
1. Future model changes → `alembic revision --autogenerate -m "description"`
2. Always review generated migrations before applying
3. Commit migration files to git
4. Run `alembic upgrade head` on other environments

## Full Documentation

See `alembic/README_ALEMBIC.md` for comprehensive documentation.

