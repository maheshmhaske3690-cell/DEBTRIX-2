"""
Run this as a separate process from the API server:

    python -m app.workers.worker_entry

It listens on the "scans" queue and executes scan jobs as they're
enqueued by the API (see app/core/queue.py).
"""
from rq import Worker

from app.core.queue import redis_conn, scan_queue

if __name__ == "__main__":
    worker = Worker([scan_queue], connection=redis_conn)
    worker.work()
