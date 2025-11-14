#!/usr/bin/env python3
"""
Database Initialization Script

This script creates all database tables using SQLAlchemy models.
It runs once during Docker Compose startup via the db-init service.
"""

import os
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/db")
sys.path.insert(0, "/app/libs/common/src")

from sqlalchemy import create_engine
from db.models.models import Base

db_user = os.getenv("POSTGRES_USER", "postgres")
db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
db_host = os.getenv("POSTGRES_HOST", "postgres")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "eth_indexer")

DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


try:

    engine = create_engine(DATABASE_URL)
    
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    
    print("DATABASE INITIALIZED SUCCESSFULLY")
    
except Exception as e:
    print("DATABASE INITIALIZATION FAILED")
    print(f"Error: {e}")
    sys.exit(1)
