import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Shared SQLAlchemy engine (connection pool)
DATABASE_URL = (
  f"postgresql://{os.getenv('POSTGRES_USER')}"
  f":{os.getenv('POSTGRES_PASSWORD')}"
  f"@{os.getenv('POSTGRES_HOST')}"
  f":{os.getenv('POSTGRES_PORT')}"
  f"/{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db_connection():
  """Get a psycopg2 connection to Postgres (for migrations)."""
  return psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=int(os.getenv("POSTGRES_PORT")),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
  )


def execute_sql_file(filepath: str):
  """Execute a SQL file against the database."""
  conn = get_db_connection()
  cur = conn.cursor()
  try:
    with open(filepath, 'r') as f:
      sql = f.read()
    cur.execute(sql)
    conn.commit()
    print(f"Successfully executed {filepath}")
  except Exception as e:
    conn.rollback()
    print(f"Error executing {filepath}: {e}")
    raise
  finally:
    cur.close()
    conn.close()

