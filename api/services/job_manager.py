import threading
import time
import uuid
import logging
from typing import Dict, Any

from api.models import BackgroundJob

logger = logging.getLogger(__name__)

_jobs_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def _now_ts():
    return time.time()


def _to_serializable_job(record: BackgroundJob) -> Dict[str, Any]:
    return {
        'job_id': str(record.id),
        'owner': record.owner_email,
        'payload': None,
        'state': record.state,
        'total': record.total,
        'processed': record.processed,
        'success': record.success,
        'failed': record.failed,
        'items': list(record.items or []),
        'error': record.error,
        'created_at': record.created_at.timestamp(),
        'updated_at': record.updated_at.timestamp(),
        'cancel': record.cancel,
    }


def _persist_job_snapshot(job: Dict[str, Any]):
    try:
        BackgroundJob.objects.update_or_create(
            id=job['job_id'],
            defaults={
                'owner_email': job['owner'],
                'state': job['state'],
                'total': job.get('total', 0),
                'processed': job.get('processed', 0),
                'success': job.get('success', 0),
                'failed': job.get('failed', 0),
                'items': list(job.get('items') or []),
                'error': job.get('error'),
                'cancel': bool(job.get('cancel', False)),
            },
        )
    except Exception as exc:
        logger.warning("Could not persist background job '%s': %s", job.get('job_id'), exc)


def _ensure_job_loaded(job_id: str):
    with _jobs_lock:
        if job_id in _jobs:
            return

    try:
        record = BackgroundJob.objects.filter(id=job_id).first()
    except Exception:
        record = None

    if not record:
        return

    with _jobs_lock:
        if job_id not in _jobs:
            _jobs[job_id] = _to_serializable_job(record)


def create_job(payload: dict, owner_email: str) -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        job = {
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
        _jobs[job_id] = job

    _persist_job_snapshot(job)
    return job_id


def get_job(job_id: str) -> Dict[str, Any]:
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        return _jobs.get(job_id)


def set_total(job_id: str, total: int):
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j is None:
            return
        j['total'] = total
        j['updated_at'] = _now_ts()

    _persist_job_snapshot(j)


def update_progress(job_id: str, *, index: int = None, email: str = None, status: str = None, message: str = None):
    _ensure_job_loaded(job_id)
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

    _persist_job_snapshot(j)


def mark_running(job_id: str):
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['state'] = 'running'
            j['updated_at'] = _now_ts()

    if j:
        _persist_job_snapshot(j)


def mark_done(job_id: str, result: dict = None):
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['state'] = 'done'
            if result:
                summary = result.get('summary', result)
                j['total'] = summary.get('total', j['total'])
                j['success'] = summary.get('success', j['success'])
                j['failed'] = summary.get('failed', j['failed'])
            j['updated_at'] = _now_ts()

    if j:
        _persist_job_snapshot(j)


def mark_error(job_id: str, error: str):
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['state'] = 'error'
            j['error'] = str(error)
            j['items'].append({
                'index': j.get('processed'),
                'email': None,
                'status': 'failed',
                'message': str(error),
                'ts': _now_ts(),
            })
            if len(j['items']) > 200:
                j['items'] = j['items'][-200:]
            j['updated_at'] = _now_ts()

    if j:
        _persist_job_snapshot(j)


def cancel_job(job_id: str):
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j['cancel'] = True
            j['updated_at'] = _now_ts()

    if j:
        _persist_job_snapshot(j)


def is_canceled(job_id: str) -> bool:
    _ensure_job_loaded(job_id)
    with _jobs_lock:
        j = _jobs.get(job_id)
        return bool(j and j.get('cancel'))


def run_job_in_thread(job_id: str):
    # Lazy imports para evitar ciclos
    from .email_service import EmailService
    from .whatsapp_service import WhatsAppService

    def _runner():
        mark_running(job_id)
        job = get_job(job_id)
        payload = job.get('payload') if job else {}
        if isinstance(payload, dict):
            payload['_job_id'] = job_id
        channel = (payload or {}).get('channel', 'email')
        try:
            print(f"[JOB {job_id}] Starting job with payload: {payload}")
            if channel == 'whatsapp':
                result = WhatsAppService.send(payload)
            else:
                result = EmailService.send(payload, job_id=job_id)

            if isinstance(result, dict) and result.get('status') == 'error':
                error_message = result.get('error') or 'Falha ao processar envio'
                mark_error(job_id, error_message)
                return

            mark_done(job_id, result)
        except Exception as e:
            mark_error(job_id, str(e))

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return t
