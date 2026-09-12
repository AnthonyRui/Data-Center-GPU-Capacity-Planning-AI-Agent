"""CLI setup and session tests without API access. / 无需 API 的 CLI 配置与会话测试。"""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_agent
from agent.demo import DemoClient
from agent.llm_client import ConfigurationError, Settings


class RunAgentTests(unittest.TestCase):
    def invoke(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", errors):
            code = run_agent.main(args)
        return code, output.getvalue(), errors.getvalue()

    def test_offline_json_demo_explicitly_identifies_itself(self):
        code, output, errors = self.invoke(["--demo", "baseline", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("OFFLINE SCRIPTED DEMO", errors)
        result = json.loads(output)
        self.assertEqual(result["records"][0]["result"]["total_gpus"], 226304)

    def test_missing_configuration_gives_actionable_help(self):
        with patch(
            "agent.llm_client.Settings.load",
            side_effect=ConfigurationError("Missing config / 缺少配置"),
        ):
            code, _, errors = self.invoke([])
        self.assertEqual(code, 2)
        self.assertIn("--configure", errors)
        self.assertIn("--demo", errors)

    def test_check_config_does_not_create_provider(self):
        with (
            patch(
                "agent.llm_client.Settings.load",
                return_value=Settings("TEST_SECRET", "test-model"),
            ),
            patch("agent.llm_client.OpenAIClient") as client,
        ):
            code, output, _ = self.invoke(["--check-config"])
        self.assertEqual(code, 0)
        self.assertNotIn("TEST_SECRET", output)
        client.assert_not_called()

    def test_configure_saves_only_local_file_without_echo(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(run_agent, "ROOT", Path(tmp)),
            patch("builtins.input", side_effect=["", ""]),
            patch("getpass.getpass", return_value="TEST_SECRET"),
        ):
            code, output, errors = self.invoke(["--configure"])
            self.assertEqual(code, 0)
            self.assertIn(
                'LLM_API_KEY="TEST_SECRET"',
                (Path(tmp) / ".env").read_text(encoding="utf-8"),
            )
            self.assertNotIn("TEST_SECRET", output + errors)
            settings = Settings.load(Path(tmp), {})
            self.assertEqual(settings.provider, "openrouter")
            self.assertEqual(settings.model, "openrouter/free")

    def test_configure_never_overwrites_existing_file(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(run_agent, "ROOT", Path(tmp)),
        ):
            path = Path(tmp) / ".env"
            path.write_text("original", encoding="utf-8")
            code, _, _ = self.invoke(["--configure"])
            self.assertEqual(code, 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "original")

    def test_interactive_commands_and_question(self):
        demo = DemoClient("baseline")
        demo.close = lambda: None
        inputs = iter(
            [
                "/help",
                "/baseline on",
                "Use baseline",
                "/reset",
                "/baseline off",
                "/exit",
            ]
        )
        with (
            patch(
                "agent.llm_client.Settings.load",
                return_value=Settings("TEST_SECRET", "test-model"),
            ),
            patch("agent.llm_client.OpenAIClient", return_value=demo),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
        ):
            code, output, _ = self.invoke([])
        self.assertEqual(code, 0)
        self.assertIn("226304", output)
        self.assertIn("会话已清空", output)
        self.assertNotIn("TEST_SECRET", output)

    def test_eof_exits_cleanly(self):
        demo = DemoClient("baseline")
        demo.close = lambda: None
        with (
            patch(
                "agent.llm_client.Settings.load",
                return_value=Settings("TEST_SECRET", "test-model"),
            ),
            patch("agent.llm_client.OpenAIClient", return_value=demo),
            patch("builtins.input", side_effect=EOFError),
        ):
            code, output, _ = self.invoke([])
        self.assertEqual(code, 0)
        self.assertIn("已退出", output)
