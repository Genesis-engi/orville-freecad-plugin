"""Job state helpers for Orville CAD jobs."""

from __future__ import annotations

ACTIVE_STATUSES = {"queued", "running"}
TERMINAL_STATUSES = {"completed", "failed"}


def job_status(job: dict) -> str:
    return str((job or {}).get("status") or "").lower()


def is_job_active(job: dict) -> bool:
    return job_status(job) in ACTIVE_STATUSES


def is_job_terminal(job: dict) -> bool:
    return job_status(job) in TERMINAL_STATUSES


def step_artifacts(job: dict) -> list[dict]:
    artifacts = (job or {}).get("artifacts") or []
    return [
        artifact
        for artifact in artifacts
        if str(artifact.get("kind") or "").lower() == "step"
        or str(artifact.get("filename") or "").lower().endswith((".step", ".stp"))
    ]
