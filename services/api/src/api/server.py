import os
from typing import cast

from common.failedjob import FailedJobManager
from common.queue import RedisQueueManager
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from web3 import Web3
from web3.types import FilterParams

from db.models.models import BlockJob, JobType, LogJob

load_dotenv()

app = Flask(__name__)
CORS(app)
redis_client = RedisQueueManager()

http_url = os.getenv("ETH_HTTP_URL")
if http_url:
    web3 = Web3(Web3.HTTPProvider(http_url))
else:
    web3 = None


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "ethereum-indexer-api"})


@app.route("/api/redrive-blocks", methods=["POST"])
def redrive_failed_jobs():
    try:
        failed_blocks = FailedJobManager("blocks", JobType.BLOCK)
        success = failed_blocks.redrive_failed_jobs()

        if success:
            return jsonify({"status": "starting redrive on failed blocks"}), 200
        else:
            return jsonify({"status": "internal server error"}), 500
    except Exception as e:
        return jsonify({"error": "Failed to redrive blocks", "details": str(e)}), 500


@app.route("/api/redrive-logs", methods=["POST"])
def redrive_failed_logs():
    try:
        failed_logs = FailedJobManager("logs", JobType.LOG)
        success = failed_logs.redrive_failed_jobs()

        if success:
            return jsonify({"status": "starting redrive on failed logs"}), 200
        else:
            return jsonify({"status": "internal server error"}), 500
    except Exception as e:
        return jsonify({"error": "Failed to redrive logs", "details": str(e)}), 500


@app.route("/api/backfill", methods=["POST"])
def backfill():
    """
    Unified backfill endpoint - queues both blocks AND logs for a range.

    Request body:
    {
        "start": 12345,          # Required: start block
        "end": 12445,            # Required: end block
        "batch_size": 100        # Optional: log batch size 1-1000 (default: 100)
    }
    """
    if not web3:
        return jsonify({"error": "Web3 not configured. Check ETH_HTTP_URL"}), 500

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

    MAX_LOG_RANGE = 50000
    block_count = end - start + 1

    if block_count > MAX_LOG_RANGE:
        return (
            jsonify(
                {
                    "error": f"Range too large. Maximum {MAX_LOG_RANGE} blocks allowed",
                    "requested": block_count,
                }
            ),
            400,
        )

    batch_size = data.get("batch_size", 100)
    try:
        batch_size = int(batch_size)
        if batch_size < 1 or batch_size > 1000:
            return jsonify({"error": "batch_size must be between 1 and 1000"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "batch_size must be an integer"}), 400

    try:
        blocks_queued = 0
        for i in range(start, end + 1):
            job_id = f"block:{i}"
            job_data: BlockJob = {
                "job_type": JobType.BLOCK.value,
                "block_number": i,
                "block_hash": "",
                "status": "new",
            }
            redis_client.push_json("blocks", job_id, job_data)
            blocks_queued += 1

        log_filter: dict = {}

        total_logs = 0
        current_block = start
        current_batch_size = batch_size
        block_timestamp_cache = {}

        while current_block <= end:
            batch_end = min(current_block + current_batch_size - 1, end)

            log_filter["fromBlock"] = current_block
            log_filter["toBlock"] = batch_end

            try:
                logs = web3.eth.get_logs(cast(FilterParams, log_filter))

                for log in logs:
                    block_number = log.get("blockNumber")
                    if not block_number:
                        continue

                    if block_number not in block_timestamp_cache:
                        try:
                            block_data = web3.eth.get_block(block_number)
                            timestamp = block_data.get("timestamp", 0)
                            block_timestamp_cache[block_number] = (
                                int(timestamp) if timestamp else 0
                            )
                        except Exception as e:
                            print(
                                f"Warning: Could not fetch timestamp for block {block_number}: {e}"
                            )
                            block_timestamp_cache[block_number] = 0

                    block_timestamp = block_timestamp_cache[block_number]

                    tx_hash = log["transactionHash"]
                    job_id = f"log:{tx_hash.hex() if hasattr(tx_hash, 'hex') else tx_hash}:{log['logIndex']}"

                    block_hash_raw = log.get("blockHash", b"")
                    block_hash = (
                        block_hash_raw.hex()
                        if hasattr(block_hash_raw, "hex")
                        else str(block_hash_raw)
                    )

                    data_raw = log.get("data", "0x")
                    data_str = (
                        data_raw.hex() if hasattr(data_raw, "hex") else str(data_raw)
                    )

                    tx_hash_raw = log.get("transactionHash", b"")
                    tx_hash_str = (
                        tx_hash_raw.hex()
                        if hasattr(tx_hash_raw, "hex")
                        else str(tx_hash_raw)
                    )

                    job: LogJob = {
                        "job_type": JobType.LOG.value,
                        "address": log.get("address", ""),
                        "block_number": block_number,
                        "block_hash": block_hash,
                        "block_timestamp": block_timestamp,
                        "data": data_str,
                        "log_index": log.get("logIndex", 0),
                        "topics": [
                            (topic.hex() if hasattr(topic, "hex") else str(topic))
                            for topic in log.get("topics", [])
                        ],
                        "transaction_hash": tx_hash_str,
                        "transaction_index": log.get("transactionIndex", 0),
                    }

                    redis_client.push_json("logs", job_id, job)
                    total_logs += 1

                current_block = batch_end + 1
                current_batch_size = batch_size

            except Exception as e:
                error_str = str(e)

                if "-32005" in error_str or "more than 10000 results" in error_str:
                    current_batch_size = max(1, current_batch_size // 2)

                    if current_batch_size < 10:
                        return (
                            jsonify(
                                {
                                    "error": "Unable to fetch logs - too many logs even in small batches",
                                    "details": error_str,
                                    "failed_at_block": current_block,
                                    "blocks_queued": blocks_queued,
                                    "logs_queued": total_logs,
                                    "hint": "Try a smaller block range or contact support",
                                }
                            ),
                            500,
                        )
                    continue
                else:
                    return (
                        jsonify(
                            {
                                "error": "Failed to fetch logs from blockchain",
                                "details": error_str,
                                "failed_at_block": current_block,
                                "blocks_queued": blocks_queued,
                                "logs_queued": total_logs,
                            }
                        ),
                        500,
                    )

        return (
            jsonify(
                {
                    "status": "success",
                    "blocks_queued": blocks_queued,
                    "logs_queued": total_logs,
                    "start_block": start,
                    "end_block": end,
                    "message": f"Queued {blocks_queued} blocks and {total_logs} logs for processing",
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": "Failed to backfill", "details": str(e)}), 500
