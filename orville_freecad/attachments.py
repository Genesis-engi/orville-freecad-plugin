"""Validation helpers for Orville image attachments."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Iterable, List


MAX_IMAGE_COUNT = 5
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


class InvalidImageAttachmentError(ValueError):
    """Raised when one or more selected image attachments are invalid."""

    def __init__(self, errors: List[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ImageAttachment:
    path: str
    filename: str
    content_type: str
    size_bytes: int


def content_type_for_path(path: str) -> str:
    _, extension = os.path.splitext(path)
    return CONTENT_TYPES.get(extension.lower(), "application/octet-stream")


def build_image_attachments(paths: Iterable[str]) -> List[ImageAttachment]:
    attachments = []
    for path in paths or []:
        filename = os.path.basename(path)
        size_bytes = os.path.getsize(path) if os.path.exists(path) else 0
        attachments.append(
            ImageAttachment(
                path=path,
                filename=filename,
                content_type=content_type_for_path(path),
                size_bytes=size_bytes,
            )
        )
    validate_image_attachments(attachments)
    return attachments


def validate_image_attachments(attachments: Iterable[ImageAttachment]) -> None:
    images = list(attachments or [])
    errors = []

    if len(images) > MAX_IMAGE_COUNT:
        errors.append(f"Attach at most {MAX_IMAGE_COUNT} images.")

    for image in images:
        if not os.path.exists(image.path):
            errors.append(f"Image does not exist: {image.path}")
            continue

        if image.content_type not in CONTENT_TYPES.values():
            errors.append(f"Unsupported image type: {image.filename}")

        if image.size_bytes > MAX_IMAGE_SIZE_BYTES:
            errors.append(f"Image is larger than 10 MB: {image.filename}")

    if errors:
        raise InvalidImageAttachmentError(errors)
