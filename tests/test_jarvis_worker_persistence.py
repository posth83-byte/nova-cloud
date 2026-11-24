import unittest

from jarvis_worker_persistence import (
    build_worker_retry_update,
    final_qa_readback_matches,
    persisted_job_matches,
)


class WorkerPersistenceTests(unittest.TestCase):
    def test_terminal_result_requires_matching_id_status_and_result(self):
        row = {"id": "job-123", "status": "completed", "result": {"reply": "klart"}}
        self.assertTrue(persisted_job_matches(row, "job-123", "completed"))
        self.assertFalse(persisted_job_matches(row, "job-456", "completed"))
        self.assertFalse(persisted_job_matches(row, "job-123", "failed"))
        self.assertFalse(persisted_job_matches(
            {"id": "job-123", "status": "completed", "result": None},
            "job-123", "completed"
        ))

    def test_final_qa_readback_requires_matching_job_and_status(self):
        row = {
            "id": "job-123",
            "status": "completed",
            "result": {"qa_evidence": {"final_result_readback": {
                "verified": True, "job_id": "job-123", "status": "completed"
            }}}
        }
        self.assertTrue(final_qa_readback_matches(row, "job-123", "completed"))
        self.assertFalse(final_qa_readback_matches(row, "job-456", "completed"))
        self.assertFalse(final_qa_readback_matches(row, "job-123", "failed"))
        self.assertFalse(final_qa_readback_matches(
            {"id": "job-123", "status": "completed", "result": {"qa_evidence": {}}},
            "job-123", "completed"
        ))

    def test_retry_clears_stale_terminal_result_and_team_lists(self):
        retrying, update = build_worker_retry_update(
            1, 3, "readback failed", "2026-11-24T06:00:00+00:00"
        )
        self.assertTrue(retrying)
        self.assertEqual(update["status"], "queued")
        self.assertIsNone(update["result"])
        self.assertEqual(update["active"], [])
        self.assertEqual(update["completed"], [])
        self.assertIsNone(update["completed_at"])
        self.assertEqual(update["error"], "readback failed")

    def test_exhausted_retries_mark_job_failed(self):
        retrying, update = build_worker_retry_update(
            3, 3, "final failure", "2026-11-24T06:00:00+00:00"
        )
        self.assertFalse(retrying)
        self.assertEqual(update["status"], "failed")
        self.assertEqual(update["completed_at"], "2026-11-24T06:00:00+00:00")
        self.assertNotIn("result", update)


if __name__ == "__main__":
    unittest.main()
