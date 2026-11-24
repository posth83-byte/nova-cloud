import unittest

from system_engineer_delivery import apply_exact_text_patches, build_source_excerpt
from system_engineer_delivery import select_independent_review_provider


class SystemEngineerDeliveryTests(unittest.TestCase):
    def test_runtime_quality_review_ignores_secondary_commit_false_positive(self):
        from system_engineer_delivery import normalize_runtime_quality_review
        evidence = {
            "runtime_verified": True,
            "requested_endpoints": [
                "/api/status", "/api/jarvis/intelligence", "/api/worker/status",
                "/api/memory/status", "/api/team/status"
            ],
            "endpoint_captures": [
                {"endpoint": path, "verified": True, "http_status": 200}
                for path in (
                    "/api/jarvis/intelligence", "/api/worker/status",
                    "/api/memory/status", "/api/team/status"
                )
                for _ in ("runtime_endpoints", "post_qa_runtime_endpoints")
            ],
        }
        review = {
            "passed": False,
            "gaps": ["Sekundära endpoints saknar deployment_commit"],
            "final_report": "Sekundära endpoints saknar deployment_commit.",
            "repair_instructions": {"QA_ENGINEER": "Lägg till commitfält."},
        }
        normalized = normalize_runtime_quality_review(
            review, evidence,
            ["/api/status deployment_commit måste matcha committen"]
        )
        self.assertTrue(normalized["passed"])
        self.assertEqual(normalized["gaps"], [])
        self.assertEqual(normalized["repair_instructions"], {})

    def test_runtime_quality_review_keeps_real_unrelated_gaps(self):
        from system_engineer_delivery import normalize_runtime_quality_review
        evidence = {
            "runtime_verified": True,
            "requested_endpoints": ["/api/status", "/api/worker/status"],
            "endpoint_captures": [
                {"endpoint": "/api/worker/status", "verified": True, "http_status": 200},
                {"endpoint": "/api/worker/status", "verified": True, "http_status": 200},
            ],
        }
        review = {
            "passed": False,
            "gaps": [
                "Sekundär endpoint saknar deployment_commit",
                "Mobil layout har ett konkret navigeringsfel",
            ],
            "final_report": "Ett mobilnavigeringsfel kvarstår.",
        }
        normalized = normalize_runtime_quality_review(
            review, evidence,
            ["/api/status deployment_commit matchar committen"]
        )
        self.assertFalse(normalized["passed"])
        self.assertEqual(normalized["gaps"], ["Mobil layout har ett konkret navigeringsfel"])

    def test_runtime_payload_summary_keeps_only_safe_fields(self):
        from system_engineer_delivery import summarize_runtime_payload
        payload = {
            "status": "online",
            "worker_running": True,
            "queue_storage": "supabase",
            "access_token": "must-not-be-copied",
            "service_role_key": "must-not-be-copied",
        }
        summary = summarize_runtime_payload("/api/worker/status", payload)
        self.assertEqual(summary, {
            "status": "online",
            "worker_running": True,
            "queue_storage": "supabase",
        })
        self.assertNotIn("access_token", summary)
        self.assertNotIn("service_role_key", summary)

    def test_route_detector_ignores_string_mentions_and_requires_real_decorator(self):
        from system_engineer_delivery import has_route_decorator
        decoy = 'markers = (\n    \'@app.get("/api/status")\',\n)'
        self.assertFalse(has_route_decorator(decoy, "/api/status"))
        self.assertTrue(has_route_decorator(
            '4015: @app.get("/api/status")',
            "/api/status"
        ))
        self.assertFalse(has_route_decorator(
            '4015: @app.post("/api/status")',
            "/api/status"
        ))

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

    def test_normalizes_supported_patch_list_aliases(self):
        from system_engineer_delivery import normalize_patch_spec
        patch = {"summary": "fix", "patches": [
            {"path": "main.py", "old_text": "a = 1", "new_text": "a = 2"}
        ]}
        normalized = normalize_patch_spec(patch)
        self.assertEqual(normalized["changes"], patch["patches"])

    def test_normalizes_root_patch_list(self):
        from system_engineer_delivery import normalize_patch_spec
        changes = [{"path": "main.py", "old_text": "a = 1", "new_text": "a = 2"}]
        self.assertEqual(normalize_patch_spec(changes)["changes"], changes)

    def test_rejects_missing_patch_list_without_alias(self):
        from system_engineer_delivery import normalize_patch_spec
        with self.assertRaisesRegex(ValueError, "saknar en giltig changes-lista"):
            normalize_patch_spec({"summary": "no patch provided"})

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
    def test_runtime_evidence_accepts_exact_machine_verified_match(self):
        from system_engineer_delivery import is_runtime_evidence_verified
        self.assertTrue(is_runtime_evidence_verified({
            "status": "verified",
            "http_status": 200,
            "deployment_commit": "e00f3408175e",
        }, "e00f3408175ec6717ca58497f6dba59627c418e4", True))

    def test_runtime_evidence_rejects_false_or_incomplete_approval(self):
        from system_engineer_delivery import is_runtime_evidence_verified
        commit = "e00f3408175ec6717ca58497f6dba59627c418e4"
        valid = {"status": "verified", "http_status": 200, "deployment_commit": "e00f3408175e"}
        invalid_cases = [
            ({**valid, "deployment_commit": "fc15ba55b186"}, True),
            ({**valid, "http_status": 500}, True),
            ({**valid, "status": "failed"}, True),
            ({**valid, "deployment_commit": ""}, True),
            ({**valid, "http_status": "not-a-number"}, True),
            (valid, False),
            ({"status": "verified", "http_status": 200}, True),
        ]
        for evidence, source_verified in invalid_cases:
            with self.subTest(evidence=evidence, source_verified=source_verified):
                self.assertFalse(is_runtime_evidence_verified(evidence, commit, source_verified))

    def test_runtime_evidence_is_not_required_for_unrelated_tasks(self):
        from system_engineer_delivery import is_runtime_evidence_verified
        self.assertTrue(is_runtime_evidence_verified({}, "", False, required=False))

    def test_evidence_reconciliation_accepts_machine_verified_runtime_despite_specialist_tool_limit(self):
        from system_engineer_delivery import build_evidence_reconciliation
        evidence = {
            "source_snapshot_status": "fetched",
            "source_commit_sha": "a5e2696656d3b0adc8bcdaa3e1b4671860066ec8",
            "source_files_fetched": ["main.py"],
            "status_route_in_qa_source": True,
            "runtime_status_endpoint": {
                "status": "verified", "http_status": 200,
                "deployment_commit": "a5e2696656d3"
            },
            "post_qa_status_endpoint": {
                "status": "verified", "http_status": 200,
                "deployment_commit": "a5e2696656d3"
            }
        }
        result = build_evidence_reconciliation(
            "Verifiera /api/status live efter driftsättning och HTTP",
            evidence,
            [{"target": "SYSTEM_ENGINEER", "reply": "Jag saknar direkt nätverksåtkomst."}]
        )
        self.assertEqual(result["runtime_status"], "verified")
        self.assertTrue(result["runtime_verified"])
        self.assertTrue(result["specialist_reports_are_not_runtime_evidence"])

    def test_evidence_reconciliation_fails_closed_on_mismatch_or_missing_source(self):
        from system_engineer_delivery import build_evidence_reconciliation
        base = {
            "source_snapshot_status": "fetched",
            "source_commit_sha": "a5e2696656d3b0adc8bcdaa3e1b4671860066ec8",
            "source_files_fetched": ["main.py"],
            "status_route_in_qa_source": True,
            "runtime_status_endpoint": {
                "status": "verified", "http_status": 200,
                "deployment_commit": "a5e2696656d3"
            }
        }
        mismatched = {**base, "post_qa_status_endpoint": {
            "status": "verified", "http_status": 200, "deployment_commit": "deadbeefdead"
        }}
        result = build_evidence_reconciliation(
            "Verifiera /api/status live efter driftsättning",
            mismatched
        )
        self.assertEqual(result["runtime_status"], "blocked")
        self.assertFalse(result["runtime_verified"])
        missing_source = {**base, "source_files_fetched": []}
        result = build_evidence_reconciliation(
            "Verifiera /api/status live efter driftsättning",
            missing_source
        )
        self.assertEqual(result["runtime_status"], "blocked")
        self.assertFalse(result["runtime_verified"])

    def test_driftbevis_task_requires_runtime_even_without_the_word_live(self):
        from system_engineer_delivery import build_evidence_reconciliation
        task = (
            "Kontrollera endast tillgängliga driftbevis för /api/status, "
            "/api/jarvis/intelligence, /api/worker/status, /api/memory/status "
            "och /api/team/status. Rapportera deployment_commit och worker_running."
        )
        result = build_evidence_reconciliation(task, {
            "source_snapshot_status": "fetched",
            "source_commit_sha": "1a367f84acb61cb5fe48fc01c658e3d19f0a38a9",
            "source_files_fetched": ["main.py"],
            "status_route_in_qa_source": True,
            "runtime_routes_in_qa_source": [
                "/api/status", "/api/jarvis/intelligence", "/api/worker/status",
                "/api/memory/status", "/api/team/status"
            ],
            "runtime_status_endpoint": {
                "status": "verified", "http_status": 200,
                "deployment_commit": "1a367f84acb6"
            },
            "post_qa_status_endpoint": {
                "status": "verified", "http_status": 200,
                "deployment_commit": "1a367f84acb6"
            }
        })
        self.assertTrue(result["runtime_required"])
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(result["runtime_status"], "blocked")
        self.assertEqual(len(result["endpoint_captures"]), 8)

    def test_evidence_reconciliation_requires_each_requested_endpoint_twice(self):
        from system_engineer_delivery import build_evidence_reconciliation
        task = "Verifiera /api/status live samt /api/worker/status och /api/team/status"
        evidence = {
            "source_snapshot_status": "fetched",
            "source_commit_sha": "1a367f84acb61cb5fe48fc01c658e3d19f0a38a9",
            "source_files_fetched": ["main.py"],
            "status_route_in_qa_source": True,
            "runtime_routes_in_qa_source": ["/api/status", "/api/worker/status", "/api/team/status"],
            "runtime_status_endpoint": {"status": "verified", "http_status": 200, "deployment_commit": "1a367f84acb6"},
            "post_qa_status_endpoint": {"status": "verified", "http_status": 200, "deployment_commit": "1a367f84acb6"},
            "runtime_endpoints": {
                "/api/worker/status": {"status": "verified", "http_status": 200},
                "/api/team/status": {"status": "verified", "http_status": 200}
            },
            "post_qa_runtime_endpoints": {
                "/api/worker/status": {"status": "verified", "http_status": 200},
                "/api/team/status": {"status": "verified", "http_status": 200}
            }
        }
        result = build_evidence_reconciliation(task, evidence)
        self.assertTrue(result["runtime_verified"])
        evidence["post_qa_runtime_endpoints"]["/api/team/status"]["http_status"] = 503
        result = build_evidence_reconciliation(task, evidence)
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(result["runtime_status"], "blocked")

    def test_evidence_reconciliation_marks_unrelated_tasks_not_required(self):
        from system_engineer_delivery import build_evidence_reconciliation
        result = build_evidence_reconciliation("Bygg en inköpslista", {})
        self.assertEqual(result["runtime_status"], "not_required")
        self.assertIsNone(result["runtime_verified"])

    def test_source_excerpt_keeps_relevant_worker_context(self):
        source = (
            "start\n"
            "async def jarvis_job_worker_loop():\n"
            "    return True\n"
            '@app.post("/api/jarvis/jobs")\n'
            "def create_job():\n"
            "    return True\n"
            '@app.get("/api/status")\n'
            "async def status():\n"
            "    return {\"status\": \"online\"}\n"
        )
        excerpt = build_source_excerpt(source)
        self.assertIn("async def jarvis_job_worker_loop", excerpt)
        self.assertIn('/api/jarvis/jobs', excerpt)
        self.assertIn('/api/status', excerpt)


if __name__ == "__main__":
    unittest.main()
