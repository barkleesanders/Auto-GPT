"""Software checks: no autonomous loop, provider requests, or physical audio."""

import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["PYTHON_DOTENV_DISABLED"] = "1"


class OfflineTests(unittest.TestCase):
    def test_file_operations_stay_inside_temporary_workspace(self):
        import file_operations

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(file_operations, "working_directory", directory),
        ):
            self.assertEqual(
                file_operations.write_to_file("nested/note.txt", "one"),
                "File written to successfully.",
            )
            self.assertEqual(
                file_operations.append_to_file("nested/note.txt", "two"),
                "Text appended successfully.",
            )
            self.assertEqual(file_operations.read_file("nested/note.txt"), "onetwo")
            self.assertEqual(
                file_operations.delete_file("nested/note.txt"),
                "File deleted successfully.",
            )
            for operation in [file_operations.read_file, file_operations.delete_file]:
                self.assertTrue(operation("../outside").startswith("Error:"))
            self.assertTrue(
                file_operations.write_to_file("../outside", "blocked").startswith(
                    "Error:"
                )
            )

    def test_container_execution_rejects_escape_before_contacting_docker(self):
        import execute_code

        with patch.object(
            execute_code.docker,
            "from_env",
            side_effect=AssertionError("Docker contacted"),
        ):
            self.assertTrue(
                execute_code.execute_python_file(
                    "../auto_gpt_workspace-other/escape.py"
                ).startswith("Error:")
            )

    def test_config_loads_dotenv_without_overwriting_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(ROOT / "scripts/config.py", root / "config.py")
            (root / ".env").write_text(
                "OPENAI_API_KEY=fixture-only\nFAST_TOKEN_LIMIT=512\nSMART_TOKEN_LIMIT=1024\n"
                'FAST_LLM_MODEL="fixture model"\n',
                encoding="utf-8",
            )
            env = {
                key: value
                for key, value in os.environ.items()
                if key
                not in {
                    "PYTHON_DOTENV_DISABLED",
                    "OPENAI_API_KEY",
                    "FAST_TOKEN_LIMIT",
                    "SMART_TOKEN_LIMIT",
                    "FAST_LLM_MODEL",
                }
            }
            env["SMART_TOKEN_LIMIT"] = "2048"
            code = (
                "import config, openai; c=config.Config(); "
                "assert c.openai_api_key == 'fixture-only'; "
                "assert openai.api_key == 'fixture-only'; "
                "assert c.fast_token_limit == 512; "
                "assert c.smart_token_limit == 2048; "
                "assert c.fast_llm_model == 'fixture model'; "
                "assert c is config.Config()"
            )
            subprocess.run([sys.executable, "-c", code], cwd=root, env=env, check=True)

    def test_all_library_modules_import_without_running_main(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            os.chdir(directory)
            try:
                for source in (ROOT / "scripts").glob("*.py"):
                    if source.stem != "main":
                        importlib.import_module(source.stem)
            finally:
                os.chdir(previous)

    def test_workspace_rejects_sibling_and_symlink_escape(self):
        from file_operations import safe_join

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            sibling = Path(directory) / "workspace-other"
            sibling.mkdir()
            (root / "link").symlink_to(sibling, target_is_directory=True)
            for path in [
                "../workspace-other/secret",
                "link/secret",
                str(sibling / "secret"),
            ]:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    safe_join(str(root), path)
            self.assertEqual(
                Path(safe_join(str(root), "nested/file.txt")),
                root.resolve() / "nested/file.txt",
            )

    def test_json_repair_keeps_validated_model_response_as_text(self):
        import json_parser

        with patch.object(json_parser, "call_ai_function", return_value='{"ok":true}'):
            self.assertEqual(json_parser.fix_and_parse_json("not json"), {"ok": True})

    def test_json_without_provider_repair(self):
        import json_parser

        with patch.object(
            json_parser, "call_ai_function", side_effect=AssertionError("provider call")
        ):
            self.assertEqual(
                json_parser.fix_and_parse_json('prefix {"ok":true} suffix', False),
                {"ok": True},
            )
            with self.assertRaises(ValueError):
                json_parser.fix_and_parse_json("not json", False)

    def test_search_adapter_preserves_duckduckgo_backend(self):
        import commands

        rows = [{"title": "fixture", "href": "https://example.com/", "body": "fixture"}]
        with patch.object(commands, "DDGS") as factory:
            search = factory.return_value.text
            search.return_value = rows
            self.assertEqual(json.loads(commands.google_search("fixture", 2)), rows)
            search.assert_called_once_with(
                "fixture", max_results=2, backend="duckduckgo"
            )

    def test_speech_adapter_uses_blocking_playback_contract(self):
        import inspect
        import playsound3
        import speak

        self.assertTrue(
            inspect.signature(playsound3.playsound).parameters["block"].default
        )
        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            os.chdir(directory)
            try:

                def save(path):
                    Path(path).write_bytes(b"synthetic audio fixture")

                with (
                    patch.object(speak.gtts, "gTTS") as tts,
                    patch.object(speak, "playsound") as play,
                ):
                    tts.return_value.save.side_effect = save
                    speak.gtts_speech("fixture")
                    play.assert_called_once_with("speech.mp3")
                    self.assertFalse(Path("speech.mp3").exists())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
