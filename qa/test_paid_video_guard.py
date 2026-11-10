"""Unit tests for the default-off paid video provider guard."""
import os
import unittest
from unittest.mock import patch

from video_cost_guard import paid_video_engines_enabled


class PaidVideoEngineGuardTests(unittest.TestCase):
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
