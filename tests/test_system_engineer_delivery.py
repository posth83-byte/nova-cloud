import unittest

from system_engineer_delivery import apply_exact_text_patches, build_source_excerpt
from system_engineer_delivery import select_independent_review_provider


class SystemEngineerDeliveryTests(unittest.TestCase):
    def test_applies_one_exact_replacement(self):
        updated, applied = apply_exact_text_patches(
            "alpha = 1\nbeta = 2\n",
            [{"path": "main.py", "old_text": "beta = 2", "new_text": "beta = 3"}],
        )
        self.assertEqual(updated, "alpha = 1\nbeta = 3\n")
        self.assertEqual(len(applied), 1)

    def test_rejects_missing_anchor(self):
        with self.assertRaisesRegex(ValueError, "0 förekomster"):
            apply_exact_text_patches(
                "alpha = 1",
                [{"path": "main.py", "old_text": "missing", "new_text": "present"}],
            )

    def test_rejects_ambiguous_anchor(self):
        with self.assertRaisesRegex(ValueError, "2 förekomster"):
            apply_exact_text_patches(
                "alpha = 1\nalpha = 1",
                [{"path": "main.py", "old_text": "alpha = 1", "new_text": "alpha = 2"}],
            )

    def test_rejects_path_outside_allowlist(self):
        with self.assertRaisesRegex(ValueError, "Otillåten filväg"):
            apply_exact_text_patches(
                "alpha = 1",
                [{"path": "requirements.txt", "old_text": "alpha = 1", "new_text": "alpha = 2"}],
            )

    def test_rejects_empty_or_oversized_patch_lists(self):
        with self.assertRaises(ValueError):
            apply_exact_text_patches("alpha = 1", [])
        with self.assertRaises(ValueError):
            apply_exact_text_patches(
                "alpha = 1",
                [{"path": "main.py", "old_text": "alpha = 1", "new_text": "x" * 10001}],
            )

    def test_review_uses_other_provider_than_patch_generator(self):
        self.assertEqual(select_independent_review_provider("Gemini", True, True), "OpenRouter")
        self.assertEqual(select_independent_review_provider("OpenRouter", True, True), "Gemini")

    def test_review_fails_closed_without_independent_provider(self):
        self.assertIsNone(select_independent_review_provider("Gemini", True, False))
        self.assertIsNone(select_independent_review_provider("OpenRouter", False, True))
        self.assertIsNone(select_independent_review_provider("unknown", True, True))

    def test_verified_noop_requires_explicit_independent_approval(self):
        from system_engineer_delivery import is_verified_noop_review
        self.assertTrue(is_verified_noop_review({
            "passed": True, "no_change_needed": True, "blockers": []
        }))
        self.assertFalse(is_verified_noop_review({
            "passed": True, "no_change_needed": False, "blockers": []
        }))
        self.assertFalse(is_verified_noop_review({
            "passed": True, "no_change_needed": True, "blockers": ["runtime not verified"]
        }))
        self.assertFalse(is_verified_noop_review({"passed": True}))
    def test_source_excerpt_keeps_relevant_worker_context(self):
        source = (
            "start\n"
            "async def jarvis_job_worker_loop():\n"
            "    return True\n"
            '@app.post("/api/jarvis/jobs")\n'
            "def create_job():\n"
            "    return True\n"
        )
        excerpt = build_source_excerpt(source)
        self.assertIn("async def jarvis_job_worker_loop", excerpt)
        self.assertIn('/api/jarvis/jobs', excerpt)


if __name__ == "__main__":
    unittest.main()
