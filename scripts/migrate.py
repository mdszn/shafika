#!/usr/bin/env python3
"""Run database migrations."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../libs/common/src"))

from common.db import execute_sql_file


def main():
    schema_file = os.path.join(os.path.dirname(__file__), "../db/schema.sql")
    if not os.path.exists(schema_file):
        print(f"Schema file not found: {schema_file}")
        sys.exit(1)

    print(f"Running migrations from {schema_file}...")
    execute_sql_file(schema_file)
    print("Migrations complete!")


if __name__ == "__main__":
    main()
