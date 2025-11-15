"""
REST API Server for Ethereum Indexer
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import desc
from common.failedjob import FailedJobManager
from db.models.models import Transfer
from common.queue import RedisQueueManager
from db.models.models import JobType, BlockJob

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
redis_client = RedisQueueManager()


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "ethereum-indexer-api"})

@app.route("/api/redrive-blocks", methods=["POST"])
def redrive_failed_jobs():
    try:
        failed_blocks = FailedJobManager('blocks', JobType.BLOCK)
        success = failed_blocks.redrive_failed_blocks()
        
        if success:
            return jsonify({"status": "starting redrive on failed blocks"}), 200
        else:
            return jsonify({"status": "internal server error"}), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to redrive blocks",
            "details": str(e)
        }), 500

    

@app.route("/api/queue-blocks", methods=["POST"])
def queue_blocks():
    """Queue a range of blocks for processing."""
    
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()

    if "start" not in data or "end" not in data:
        return jsonify({"error": "Missing required fields: start, end"}), 400

    try:
        start = int(data["start"])
        end = int(data["end"])
    except (ValueError, TypeError):
        return jsonify({"error": "start and end must be integers"}), 400

    if start < 0 or end < 0:
        return jsonify({"error": "Block numbers must be non-negative"}), 400

    if start > end:
        return jsonify({"error": "start must be <= end"}), 400

    MAX_RANGE = 10000
    block_count = end - start + 1
    if block_count > MAX_RANGE:
        return (
            jsonify(
                {
                    "error": f"Range too large. Maximum {MAX_RANGE} blocks allowed",
                    "requested": block_count,
                }
            ),
            400,
        )

    try:
        queued = 0
        for i in range(start, end + 1):
            job_id = f"block:{i}"
            job_data: BlockJob = {
                "job_type": JobType.BLOCK.value,
                "block_number": i,
                "block_hash": "/api/queue-blocks",
                "status": "new",
            }
            redis_client.push_json("blocks", job_id, job_data)
            queued += 1

        return (
            jsonify(
                {"status": "success", "queued": queued, "start": start, "end": end}
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": "Failed to queue blocks", "details": str(e)}), 500

