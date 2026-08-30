"""
Redis Queue setup. The API enqueues scan jobs here; a separate
worker process (run via `python -m app.workers.worker_entry`)
picks them up and runs app.workers.scan_worker.run_scan_job.
"""
import asyncio

import redis
from rq import Queue

from app.core.config import settings

redis_conn = redis.from_url(settings.REDIS_URL)
scan_queue = Queue("scans", connection=redis_conn)


def _run_scan_job_sync(scan_job_id: str) -> None:
    """RQ workers are sync — wrap our async scan pipeline for them."""
    from app.workers.scan_worker import run_scan_job
    asyncio.run(run_scan_job(scan_job_id))


def enqueue_scan(scan_job_id: str) -> None:
    scan_queue.enqueue(_run_scan_job_sync, scan_job_id, job_timeout=1800)
