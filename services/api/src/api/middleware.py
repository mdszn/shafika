"""
API Middleware
Handles authentication and request preprocessing.
"""

import hashlib
from functools import wraps

from common.db import SessionLocal
from flask import jsonify, request
from sqlalchemy import func

from db.models.models import Admin


def require_api_key(f):
    """
    Decorator to require API key authentication.
    API key must be provided in the X-API-Key header.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        """
        This wrapper function runs before the actual route handler.
        """
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return (
                jsonify({"error": "Unauthorized", "message": "API key is required"}),
                401,
            )

        api_key_hash = hashlib.md5(api_key.encode()).hexdigest()

        session = SessionLocal()
        try:
            admin = (
                session.query(Admin)
                .filter_by(api_key_hash=api_key_hash, is_active=True)
                .first()
            )

            if not admin:
                return (
                    jsonify({"error": "Unauthorized", "message": "Invalid API key"}),
                    401,
                )

            admin.last_used_at = func.now()
            session.commit()

        except Exception as e:
            session.rollback()
            print(f"Error verifying API key: {e}")
            return jsonify({"error": "Internal server error"}), 500
        finally:
            session.close()

        return f(*args, **kwargs)

    return decorated_function
