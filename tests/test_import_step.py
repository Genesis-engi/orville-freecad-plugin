import unittest

from orville_freecad.import_step import safe_document_name


class ImportStepTests(unittest.TestCase):
    def test_safe_document_name_removes_invalid_characters(self):
        self.assertEqual(safe_document_name("one-inch cube.step"), "one_inch_cube_step")

    def test_safe_document_name_prefixes_digit(self):
        self.assertEqual(safe_document_name("123 cube"), "Orville_123_cube")

    def test_safe_document_name_uses_default_for_empty_input(self):
        self.assertEqual(safe_document_name("!!!"), "Orville_Result")


if __name__ == "__main__":
    unittest.main()
