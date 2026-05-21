import os
import tempfile
import unittest

from orville_freecad.attachments import (
    MAX_IMAGE_COUNT,
    MAX_IMAGE_SIZE_BYTES,
    InvalidImageAttachmentError,
    build_image_attachments,
    content_type_for_path,
)


class AttachmentTests(unittest.TestCase):
    def test_content_type_for_supported_extensions(self):
        self.assertEqual(content_type_for_path("part.PNG"), "image/png")
        self.assertEqual(content_type_for_path("part.jpeg"), "image/jpeg")
        self.assertEqual(content_type_for_path("part.heif"), "image/heif")

    def test_builds_valid_attachments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "reference.png")
            with open(path, "wb") as handle:
                handle.write(b"png")

            attachments = build_image_attachments([path])

        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].filename, "reference.png")
        self.assertEqual(attachments[0].content_type, "image/png")

    def test_rejects_missing_file(self):
        with self.assertRaises(InvalidImageAttachmentError) as context:
            build_image_attachments(["/does/not/exist.png"])

        self.assertIn("does not exist", str(context.exception))

    def test_rejects_unsupported_file_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "reference.txt")
            with open(path, "wb") as handle:
                handle.write(b"text")

            with self.assertRaises(InvalidImageAttachmentError) as context:
                build_image_attachments([path])

        self.assertIn("Unsupported image type", str(context.exception))

    def test_rejects_too_many_images(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index in range(MAX_IMAGE_COUNT + 1):
                path = os.path.join(directory, f"reference-{index}.png")
                with open(path, "wb") as handle:
                    handle.write(b"png")
                paths.append(path)

            with self.assertRaises(InvalidImageAttachmentError) as context:
                build_image_attachments(paths)

        self.assertIn("Attach at most", str(context.exception))

    def test_rejects_large_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "large.png")
            with open(path, "wb") as handle:
                handle.truncate(MAX_IMAGE_SIZE_BYTES + 1)

            with self.assertRaises(InvalidImageAttachmentError) as context:
                build_image_attachments([path])

        self.assertIn("larger than 10 MB", str(context.exception))


if __name__ == "__main__":
    unittest.main()
