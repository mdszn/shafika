#!/usr/bin/env python3
"""Initialize database tables using SQLAlchemy models."""

import os
import sys

# Add project root to path
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/db")
sys.path.insert(0, "/app/libs/common/src")

from sqlalchemy import create_engine
from db.models.models import Base

# Get database connection from environment
db_user = os.getenv("POSTGRES_USER", "postgres")
db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
db_host = os.getenv("POSTGRES_HOST", "postgres")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "eth_indexer")

# Create database URL
DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

print(f"Connecting to database: {db_host}:{db_port}/{db_name}")

# Create engine and tables
engine = create_engine(DATABASE_URL)

print("Creating all tables...")
Base.metadata.create_all(engine)

print("✓ Database initialized successfully!")
print(f"✓ Created tables: {', '.join(Base.metadata.tables.keys())}")
