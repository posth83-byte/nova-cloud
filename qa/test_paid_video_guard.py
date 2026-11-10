"""Unit tests for the default-off paid video provider guard."""
import ast
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from video_cost_guard import paid_video_engines_enabled


class PaidVideoEngineGuardTests(unittest.TestCase):
    def _assert_request_is_guarded(self, filename, function_name):
        source = (Path(__file__).resolve().parents[1] / filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        )
        guard_lines = [
            node.lineno for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "paid_video_engines_enabled"
        ]
        network_lines = [
            node.lineno for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "urlopen"
        ]
        self.assertTrue(guard_lines, f"{filename}:{function_name} has no paid-provider guard")
        self.assertTrue(network_lines, f"{filename}:{function_name} has no identifiable network call")
        self.assertLess(min(guard_lines), min(network_lines))

    def test_runway_request_is_guarded_before_network(self):
        self._assert_request_is_guarded("runway_engine.py", "runway_request")

    def test_kling_request_is_guarded_before_network(self):
        self._assert_request_is_guarded("kling_engine.py", "kling_request")

    def test_missing_flag_disables_paid_engines(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(paid_video_engines_enabled())

    def test_false_values_disable_paid_engines(self):
        for value in ("false", "0", "no", "off", ""):
            with self.subTest(value=value), patch.dict(
                os.environ, {"ENABLE_PAID_VIDEO_ENGINES": value}, clear=True
            ):
                self.assertFalse(paid_video_engines_enabled())

    def test_explicit_true_values_enable_paid_engines(self):
        for value in ("true", "1", "yes", "on", "TRUE"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"ENABLE_PAID_VIDEO_ENGINES": value}, clear=True
            ):
                self.assertTrue(paid_video_engines_enabled())


if __name__ == "__main__":
    unittest.main(verbosity=2)
