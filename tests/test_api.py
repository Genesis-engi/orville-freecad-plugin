import io
import json
import os
import tempfile
import unittest
from urllib.error import HTTPError

from orville_freecad.api import OrvilleApiClient, OrvilleApiError


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


class FakeOpener:
    def __init__(self, body=b'{"id":"cadjob_123","status":"queued"}', error=None):
        self.body = body
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return FakeResponse(self.body)


class ApiClientTests(unittest.TestCase):
    def test_create_job_without_images_sends_json(self):
        opener = FakeOpener()
        client = OrvilleApiClient("secret", opener=opener)

        response = client.create_job("Create a bracket", idempotency_key="idem-1")

        request, timeout = opener.requests[0]
        self.assertEqual(response["id"], "cadjob_123")
        self.assertEqual(timeout, 60)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "https://www.ballistalabs.ai/api/v1/cad/jobs")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(request.get_header("Idempotency-key"), "idem-1")
        self.assertIn("application/json", request.get_header("Content-type"))
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"prompt": "Create a bracket"})

    def test_create_job_with_images_sends_multipart_images_field(self):
        opener = FakeOpener()
        client = OrvilleApiClient("secret", opener=opener)

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "sketch.png")
            with open(path, "wb") as handle:
                handle.write(b"png-data")

            client.create_job("Create a cup holder", [path], idempotency_key="idem-2")

        request, _ = opener.requests[0]
        body = request.data
        self.assertIn("multipart/form-data", request.get_header("Content-type"))
        self.assertIn(b'name="prompt"', body)
        self.assertIn(b'name="images"; filename="sketch.png"', body)
        self.assertIn(b"png-data", body)

    def test_create_message_uses_job_messages_endpoint(self):
        opener = FakeOpener(body=b'{"id":"cadjob_123","status":"queued","message_id":"msg_1"}')
        client = OrvilleApiClient("secret", opener=opener)

        response = client.create_message("cadjob_123", "Make it thicker", idempotency_key="idem-3")

        request, _ = opener.requests[0]
        self.assertEqual(response["message_id"], "msg_1")
        self.assertEqual(
            request.full_url,
            "https://www.ballistalabs.ai/api/v1/cad/jobs/cadjob_123/messages",
        )

    def test_http_error_parses_orville_error_shape(self):
        body = json.dumps({"error": {"code": "missing_prompt", "message": "Prompt is required"}}).encode()
        error = HTTPError("https://example.test", 400, "Bad Request", {}, io.BytesIO(body))
        opener = FakeOpener(error=error)
        client = OrvilleApiClient("secret", opener=opener)

        with self.assertRaises(OrvilleApiError) as context:
            client.get_job("cadjob_123")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.code, "missing_prompt")
        self.assertEqual(context.exception.message, "Prompt is required")

    def test_download_artifact_writes_step_file(self):
        opener = FakeOpener(body=b"ISO-10303-21;")
        client = OrvilleApiClient("secret", opener=opener)

        with tempfile.TemporaryDirectory() as directory:
            download = client.download_artifact("art_123", directory, "generated.step")
            with open(download.path, "rb") as handle:
                body = handle.read()

        request, _ = opener.requests[0]
        self.assertEqual(
            request.full_url,
            "https://www.ballistalabs.ai/api/v1/artifacts/art_123/download",
        )
        self.assertEqual(download.filename, "generated.step")
        self.assertEqual(body, b"ISO-10303-21;")


if __name__ == "__main__":
    unittest.main()
