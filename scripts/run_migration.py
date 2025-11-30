#!/usr/bin/env python3
"""Run a specific migration file."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../libs/common/src"))

from common.db import execute_sql_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file>")
        print("Example: python run_migration.py ../db/migrations/001_add_enums.sql")
        sys.exit(1)

    migration_file = sys.argv[1]

    if not os.path.exists(migration_file):
        print(f"Migration file not found: {migration_file}")
        sys.exit(1)

    print(f"Running migration: {migration_file}")
    try:
        execute_sql_file(migration_file)
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
