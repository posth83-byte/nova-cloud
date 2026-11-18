"""Small, deterministic helpers for the JARVIS background worker persistence path."""


def persisted_job_matches(row, job_id, terminal_status):
    """Return True only when the returned Supabase row matches this terminal result."""
    return bool(
        isinstance(row, dict)
        and str(row.get("id")) == str(job_id)
        and row.get("status") == terminal_status
        and row.get("result") is not None
    )


def final_qa_readback_matches(row, job_id, terminal_status):
    """Require the final QA readback marker in the persisted result itself."""
    if not persisted_job_matches(row, job_id, terminal_status):
        return False
    result = row.get("result")
    if not isinstance(result, dict):
        return False
    evidence = result.get("qa_evidence")
    if not isinstance(evidence, dict):
        return False
    final_readback = evidence.get("final_result_readback")
    return bool(
        isinstance(final_readback, dict)
        and final_readback.get("verified") is True
        and str(final_readback.get("job_id")) == str(job_id)
        and final_readback.get("status") == terminal_status
    )


def build_worker_retry_update(attempts, max_attempts, error, now_iso):
    """Build a retry/failure update without leaving a stale completed result visible."""
    retrying = int(attempts or 1) < int(max_attempts or 3)
    update = {
        "status": "queued" if retrying else "failed",
        "phase": (
            f"Automatiskt nytt försök {int(attempts or 1) + 1}/{int(max_attempts or 3)}"
            if retrying
            else "Bakgrundsarbetet misslyckades efter flera försök"
        ),
        "error": str(error)[:1500],
        "locked_at": None,
        "worker_id": None,
        "completed_at": None if retrying else now_iso,
        "updated_at": now_iso,
    }
    if retrying:
        update.update({
            "result": None,
            "active": [],
            "completed": [],
        })
    return retrying, update
