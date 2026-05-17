import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import commands


class FileOperationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        self.project_dir_patch = patch.object(commands, "PROJECT_DIR", self.project_dir)
        self.project_dir_patch.start()

    def tearDown(self):
        self.project_dir_patch.stop()
        self.temp_dir.cleanup()

    def capture_output(self, text):
        output = io.StringIO()
        with redirect_stdout(output):
            commands.handle_command(text)
        return output.getvalue()

    def test_touch_creates_file_in_project_directory(self):
        output = self.capture_output("touch notes.txt")

        self.assertTrue((self.project_dir / "notes.txt").is_file())
        self.assertIn("Created file: notes.txt", output)

    def test_mkdir_creates_folder_in_project_directory(self):
        output = self.capture_output("mkdir examples")

        self.assertTrue((self.project_dir / "examples").is_dir())
        self.assertIn("Created folder: examples", output)

    def test_copy_copies_existing_file(self):
        (self.project_dir / "notes.txt").write_text("hello")

        output = self.capture_output("cp notes.txt backup.txt")

        self.assertEqual((self.project_dir / "backup.txt").read_text(), "hello")
        self.assertIn("Copied notes.txt to backup.txt", output)

    def test_friendly_file_aliases_reuse_safe_handlers(self):
        output = self.capture_output("create file notes.txt")
        self.assertTrue((self.project_dir / "notes.txt").is_file())
        self.assertIn("Created file: notes.txt", output)

        output = self.capture_output("create folder examples")
        self.assertTrue((self.project_dir / "examples").is_dir())
        self.assertIn("Created folder: examples", output)

        (self.project_dir / "source.txt").write_text("hello")
        output = self.capture_output("copy source.txt to duplicate.txt")
        self.assertEqual((self.project_dir / "duplicate.txt").read_text(), "hello")
        self.assertIn("Copied source.txt to duplicate.txt", output)

    def test_unsafe_names_are_blocked(self):
        blocked_names = [
            "../escape.txt",
            "folder/file.txt",
            "~notes.txt",
            "*.txt",
            "file?.txt",
            "a&b.txt",
            "a|b.txt",
            "a;b.txt",
            "a$b.txt",
            "a`b.txt",
            "a>b.txt",
            "a<b.txt",
        ]

        for name in blocked_names:
            with self.subTest(name=name):
                output = self.capture_output(f'touch "{name}"')
                self.assertIn("Blocked unsafe name", output)

    def test_missing_arguments_are_requested(self):
        self.assertIn("Please provide a file name", self.capture_output("touch"))
        self.assertIn("Please provide a folder name", self.capture_output("mkdir"))
        self.assertIn("Please provide a source and destination", self.capture_output("cp notes.txt"))
        self.assertIn("Please provide a file name", self.capture_output("create file"))
        self.assertIn("Please provide a folder name", self.capture_output("create folder"))
        self.assertIn("Please use: copy source to destination", self.capture_output("copy notes.txt"))

    def test_copy_requires_existing_source_file(self):
        output = self.capture_output("cp missing.txt backup.txt")

        self.assertIn("Source file does not exist: missing.txt", output)
        self.assertFalse((self.project_dir / "backup.txt").exists())


class CommandRoutingTests(unittest.TestCase):
    @patch("commands.run_command")
    @patch("commands.predict_intent", return_value="python_version")
    def test_python_version_uses_safe_argument_list(self, _predict_intent, run_command):
        with redirect_stdout(io.StringIO()):
            commands.handle_command("python version")

        run_command.assert_called_once_with(["python3", "--version"])

    @patch("commands.run_command")
    @patch("commands.shutil.which", return_value=None)
    def test_fastfetch_fallback_uses_safe_commands(self, _which, run_command):
        with redirect_stdout(io.StringIO()):
            commands.show_fastfetch_info()

        self.assertEqual(
            [call.args[0] for call in run_command.call_args_list],
            [["uname", "-a"], ["lscpu"], ["free", "-h"], ["df", "-h"]],
        )


if __name__ == "__main__":
    unittest.main()
