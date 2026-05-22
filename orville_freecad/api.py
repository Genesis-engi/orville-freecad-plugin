"""Small standard-library client for the Orville CAD API."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid
from typing import Dict, Iterable, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, build_opener

from .attachments import ImageAttachment, build_image_attachments
from .metadata import VERSION


DEFAULT_BASE_URL = "https://www.ballistalabs.ai"
DEFAULT_TIMEOUT_SECONDS = 60
USER_AGENT = f"orville-freecad/{VERSION}"


class OrvilleApiError(RuntimeError):
    """Raised when Orville returns an error response."""

    def __init__(
        self,
        status_code: Optional[int],
        code: str,
        message: str,
        raw_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.raw_body = raw_body


@dataclass(frozen=True)
class ArtifactDownload:
    artifact_id: str
    filename: str
    path: str


class OrvilleApiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        opener=None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("Orville API key is required.")

        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self.opener = opener or build_opener()

    def create_job(
        self,
        prompt: str,
        image_paths: Optional[Iterable[str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        return self._send_prompt_request(
            "POST",
            "/api/v1/cad/jobs",
            prompt,
            image_paths,
            idempotency_key,
        )

    def create_message(
        self,
        job_id: str,
        prompt: str,
        image_paths: Optional[Iterable[str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        self._ensure_id(job_id, "job_id")
        path = f"/api/v1/cad/jobs/{quote(job_id)}/messages"
        return self._send_prompt_request("POST", path, prompt, image_paths, idempotency_key)

    def get_job(self, job_id: str) -> Dict:
        self._ensure_id(job_id, "job_id")
        return self._send_json("GET", f"/api/v1/cad/jobs/{quote(job_id)}")

    def list_jobs(
        self,
        limit: int = 20,
        cursor: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict:
        limit = max(1, min(int(limit), 100))
        params = {"limit": str(limit)}
        if cursor:
            params["cursor"] = cursor
        if query:
            params["q"] = query
        return self._send_json("GET", f"/api/v1/cad/jobs?{urlencode(params)}")

    def get_messages(self, job_id: str) -> Dict:
        self._ensure_id(job_id, "job_id")
        return self._send_json("GET", f"/api/v1/cad/jobs/{quote(job_id)}/messages")

    def list_artifacts(self, job_id: str) -> Dict:
        self._ensure_id(job_id, "job_id")
        return self._send_json("GET", f"/api/v1/cad/jobs/{quote(job_id)}/artifacts")

    def get_billing_balance(self) -> Dict:
        return self._send_json("GET", "/api/v1/billing/balance")

    def download_artifact(
        self,
        artifact_id: str,
        target_dir: str,
        filename: Optional[str] = None,
    ) -> ArtifactDownload:
        self._ensure_id(artifact_id, "artifact_id")
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        safe_filename = _safe_filename(filename or f"{artifact_id}.step")
        if not safe_filename.lower().endswith((".step", ".stp")):
            safe_filename = f"{safe_filename}.step"

        target_path = str(target / safe_filename)
        body = self._send_bytes(
            "GET",
            f"/api/v1/artifacts/{quote(artifact_id)}/download",
        )
        with open(target_path, "wb") as handle:
            handle.write(body)

        return ArtifactDownload(
            artifact_id=artifact_id,
            filename=safe_filename,
            path=target_path,
        )

    def _send_prompt_request(
        self,
        method: str,
        path: str,
        prompt: str,
        image_paths: Optional[Iterable[str]],
        idempotency_key: Optional[str],
    ) -> Dict:
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("Prompt is required.")

        idempotency_key = idempotency_key or str(uuid.uuid4())
        attachments = build_image_attachments(image_paths or [])
        headers = {"Idempotency-Key": idempotency_key}

        if attachments:
            body, content_type = _multipart_body(prompt, attachments)
            headers["Content-Type"] = content_type
        else:
            body = json.dumps({"prompt": prompt}).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        return self._send_json(method, path, body=body, headers=headers)

    def _send_json(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict:
        raw = self._send_bytes(method, path, body=body, headers=headers)
        if not raw:
            raise OrvilleApiError(None, "empty_response", "Orville returned an empty response.")

        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise OrvilleApiError(None, "invalid_response", "Orville returned invalid JSON.") from exc

    def _send_bytes(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> bytes:
        request = self._build_request(method, path, body=body, headers=headers)
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            raise _error_from_http_error(exc) from exc
        except URLError as exc:
            raise OrvilleApiError(None, "network_error", str(exc.reason)) from exc

    def _build_request(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Request:
        merged_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": USER_AGENT,
        }
        merged_headers.update(headers or {})
        url = urljoin(self.base_url, path.lstrip("/"))
        return Request(url, data=body, headers=merged_headers, method=method)

    @staticmethod
    def _ensure_id(value: str, name: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{name} is required.")


def _multipart_body(prompt: str, attachments: Iterable[ImageAttachment]) -> tuple[bytes, str]:
    boundary = f"----OrvilleFreeCAD{uuid.uuid4().hex}"
    chunks = []

    def add(value: bytes) -> None:
        chunks.append(value)

    add(f"--{boundary}\r\n".encode("ascii"))
    add(b'Content-Disposition: form-data; name="prompt"\r\n\r\n')
    add(prompt.encode("utf-8"))
    add(b"\r\n")

    for image in attachments:
        add(f"--{boundary}\r\n".encode("ascii"))
        disposition = (
            'Content-Disposition: form-data; name="images"; '
            f'filename="{_escape_header_value(image.filename)}"\r\n'
        )
        add(disposition.encode("utf-8"))
        add(f"Content-Type: {image.content_type}\r\n\r\n".encode("ascii"))
        with open(image.path, "rb") as handle:
            add(handle.read())
        add(b"\r\n")

    add(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _error_from_http_error(exc: HTTPError) -> OrvilleApiError:
    raw = exc.read().decode("utf-8", errors="replace")
    code = f"http_{exc.code}"
    message = exc.reason or "Orville API request failed."

    if raw:
        try:
            payload = json.loads(raw)
            error = payload.get("error") or {}
            code = error.get("code") or code
            message = error.get("message") or message
        except json.JSONDecodeError:
            pass

    return OrvilleApiError(exc.code, code, message, raw)


def _safe_filename(filename: str) -> str:
    candidate = os.path.basename(filename or "artifact.step")
    return "".join(char for char in candidate if char not in '\\/:*?"<>|').strip() or "artifact.step"


def _escape_header_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
