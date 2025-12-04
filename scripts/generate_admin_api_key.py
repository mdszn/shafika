#!/usr/bin/env python3
"""
Script to generate and store an admin API key.
Run this after initializing the database.
"""
import hashlib
import secrets
import sys

from common.db import SessionLocal
from db.models.models import Admin


def generate_api_key():
    """Generate a secure random API key (8 bytes = 16 hex chars)"""
    return secrets.token_hex(8)


def hash_api_key(api_key: str):
    """Hash API key using MD5"""
    return hashlib.md5(api_key.encode()).hexdigest()


def create_admin(username: str):
    """
    Create or update admin user with new API key.
    """
    session = SessionLocal()
    try:
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)

        existing_admin = session.query(Admin).filter_by(username=username).first()

        if existing_admin:
            existing_admin.api_key_hash = api_key_hash
            existing_admin.is_active = True
            session.commit()
            return (api_key, False)
        else:
            admin = Admin(username=username, api_key_hash=api_key_hash, is_active=True)
            session.add(admin)
            session.commit()
            return (api_key, True)

    except Exception as e:
        session.rollback()
        print(f"Error creating admin: {e}")
        raise
    finally:
        session.close()


def main():

    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = "admin"

    try:
        api_key, is_new = create_admin(username)

        if is_new:
            print(f"Created new admin user: {username}")
        else:
            print(f"Updated existing admin user: {username}")
        print(f"This API key will only be shown once: {api_key}.")
        print("Store it securely. You cannot retrieve it later.\n")

    except Exception as e:
        print(f"Failed to generate API key: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
