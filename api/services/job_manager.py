import threading
import time
import uuid
from typing import Dict, Any

_jobs_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def _now_ts():
    return time.time()


def create_job(payload: dict, owner_email: str) -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            'job_id': job_id,
            'owner': owner_email,
            'payload': payload,
            'state': 'queued',
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'items': [],
            'error': None,
            'created_at': _now_ts(),
            'updated_at': _now_ts(),
            'cancel': False,
        }
    return job_id


def get_job(job_id: str) -> Dict[str, Any]:
    with _jobs_lock:
        return _jobs.get(job_id)


def set_total(job_id: str, total: int):
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j is None:
            return
        j['total'] = total
        j['updated_at'] = _now_ts()


def update_progress(job_id: str, *, index: int = None, email: str = None, status: str = None, message: str = None):
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j is None:
            return
        if index is not None:
            j['processed'] = max(j['processed'], index)
        if status == 'success':
            j['success'] = j.get('success', 0) + 1
        elif status == 'failed':
            j['failed'] = j.get('failed', 0) + 1
        # append recent item state (keep only last 200 to avoid memory growth)
        if email or status or message:
            j['items'].append({'index': index, 'email': email, 'status': status, 'message': message, 'ts': _now_ts()})
            if len(j['items']) > 200:
                j['items'] = j['items'][-200:]
        j['updated_at'] = _now_ts()


def mark_running(job_id: str):
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['state'] = 'running'
            j['updated_at'] = _now_ts()


def mark_done(job_id: str, result: dict = None):
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['state'] = 'done'
            if result:
                j['total'] = result.get('total', j['total'])
                j['success'] = result.get('success', j['success'])
                j['failed'] = result.get('failed', j['failed'])
            j['updated_at'] = _now_ts()


def mark_error(job_id: str, error: str):
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['state'] = 'error'
            j['error'] = str(error)
            j['updated_at'] = _now_ts()


def cancel_job(job_id: str):
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['cancel'] = True
            j['updated_at'] = _now_ts()


def is_canceled(job_id: str) -> bool:
    with _jobs_lock:
        j = _jobs.get(job_id)
        return bool(j and j.get('cancel'))


def run_job_in_thread(job_id: str):
    # Lazily import EmailService to avoid import cycles
    from .email_service import EmailService

    def _runner():
        mark_running(job_id)
        job = get_job(job_id)
        payload = job.get('payload') if job else {}
        try:
            print(f"[JOB {job_id}] Starting job with payload: {payload}")
            result = EmailService.send(payload, job_id=job_id)
            mark_done(job_id, result)
        except Exception as e:
            mark_error(job_id, str(e))

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return t
