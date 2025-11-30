"""
Gunicorn WSGI server configuration for production deployment.
"""

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"  # Use "gevent" for async, requires gevent package
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_connections = 1000
max_requests = 1000  # Restart workers after N requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to max_requests
timeout = 120  # Workers silent for more than this many seconds are killed
graceful_timeout = 30  # Time to wait for graceful shutdown
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "ethereum-indexer-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Reload on code changes (DEVELOPMENT ONLY - disable in production)
reload = os.getenv("FLASK_ENV") == "development"


# Pre/Post fork hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"Starting Gunicorn with {workers} workers and {threads} threads per worker")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("Reloading workers...")


def worker_int(worker):
    """Called when a worker receives an INT or QUIT signal."""
    print(f"Worker {worker.pid} received INT/QUIT signal")


def worker_abort(worker):
    """Called when a worker receives a SIGABRT signal."""
    print(f"Worker {worker.pid} aborted")
