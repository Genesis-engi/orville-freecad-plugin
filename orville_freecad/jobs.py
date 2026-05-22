"""Job state helpers for Orville CAD jobs."""

from __future__ import annotations

ACTIVE_STATUSES = {"queued", "running"}
TERMINAL_STATUSES = {"completed", "failed"}
DEFAULT_POLL_DELAY_SECONDS = 60


def job_status(job: dict) -> str:
    return str((job or {}).get("status") or "").lower()


def is_job_active(job: dict) -> bool:
    return job_status(job) in ACTIVE_STATUSES


def is_job_terminal(job: dict) -> bool:
    return job_status(job) in TERMINAL_STATUSES


def poll_delay_seconds(job: dict, default_seconds: int = DEFAULT_POLL_DELAY_SECONDS) -> int:
    value = (job or {}).get("poll_after_seconds")
    if value is None:
        return default_seconds

    try:
        delay = int(value)
    except (TypeError, ValueError):
        return default_seconds

    if delay <= 0:
        return default_seconds
    return delay


def step_artifacts(job: dict) -> list[dict]:
    artifacts = (job or {}).get("artifacts") or []
    return [
        artifact
        for artifact in artifacts
        if str(artifact.get("kind") or "").lower() == "step"
        or str(artifact.get("filename") or "").lower().endswith((".step", ".stp"))
    ]


def top_level_step_artifact(job: dict) -> dict | None:
    artifacts = step_artifacts(job)

    assembly_tree = (job or {}).get("assembly_tree") or {}
    artifact_id = assembly_tree.get("artifact_id")
    if artifact_id:
        for artifact in artifacts:
            if artifact.get("id") == artifact_id:
                return artifact

        if _is_step_artifact(assembly_tree):
            return {
                "id": artifact_id,
                "label": assembly_tree.get("label"),
                "filename": assembly_tree.get("filename"),
                "kind": assembly_tree.get("kind"),
            }

    if not artifacts:
        return None

    return artifacts[0]


def _is_step_artifact(artifact: dict) -> bool:
    return str(artifact.get("kind") or "").lower() == "step" or str(
        artifact.get("filename") or ""
    ).lower().endswith((".step", ".stp"))
