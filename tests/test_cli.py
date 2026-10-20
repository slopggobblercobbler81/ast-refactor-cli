"""Unit tests for ast-refactor-cli CLI."""

import tempfile
import unittest
from pathlib import Path
from ast_refactor.cli import main


class TestCLI(unittest.TestCase):
    def test_cli_rename_check_fails_when_changes_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "app.py"
            file_path.write_text("old_name = 10\nprint(old_name)\n", encoding="utf-8")

            # With --check, if changes are detected, returncode is 1
            code = main(["rename", str(file_path), "--from", "old_name", "--to", "new_name", "--check"])
            self.assertEqual(code, 1)

            # Without --check, returncode is 0
            code2 = main(["rename", str(file_path), "--from", "old_name", "--to", "new_name"])
            self.assertEqual(code2, 0)

    def test_cli_rename_write_in_place(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "app.py"
            file_path.write_text("old_name = 10\n", encoding="utf-8")

            code = main(["rename", str(file_path), "--from", "old_name", "--to", "new_name", "-w"])
            self.assertEqual(code, 0)
            self.assertEqual(file_path.read_text(encoding="utf-8"), "new_name = 10\n")

    def test_cli_extract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "calc.py"
            file_path.write_text("def run():\n    x = 1\n    y = 2\n    return x + y\n", encoding="utf-8")

            code = main(["extract", str(file_path), "--lines", "2-3", "--name", "setup_vars", "-w"])
            self.assertEqual(code, 0)
            content = file_path.read_text(encoding="utf-8")
            self.assertIn("def setup_vars():", content)

    def test_cli_modernize(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "script.py"
            file_path.write_text("if d.has_key('k'):\n    pass\n", encoding="utf-8")

            code = main(["modernize", str(file_path), "-w"])
            self.assertEqual(code, 0)
            content = file_path.read_text(encoding="utf-8")
            self.assertEqual(content, "if 'k' in d:\n    pass\n")


if __name__ == "__main__":
    unittest.main()
