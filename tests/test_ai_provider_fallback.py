import unittest

from unittest.mock import call, patch

from ai_provider_fallback import (
    is_openrouter_budget_error,
    is_openrouter_inflight_budget_error,
    run_openrouter_with_budget_fallback,
)


class OpenRouterBudgetFallbackTests(unittest.TestCase):

    def test_retries_transient_inflight_budget_error_before_lowering_cap(self):
        attempts = []
        transient = ValueError(
            'OpenRouter API-fel 402: {"metadata":{"reason":"in_flight_budget_exhausted"}}'
        )

        def fake_ask(message, system_prompt, max_tokens, json_mode, image_data):
            attempts.append(max_tokens)
            if max_tokens == 2048:
                raise transient
            return "Svar efter att samtidiga anrop lagt sig"

        with patch("ai_provider_fallback.time.sleep") as sleep:
            answer, used_tokens = run_openrouter_with_budget_fallback(
                fake_ask, "fråga", "system", 2048
            )

        self.assertEqual(answer, "Svar efter att samtidiga anrop lagt sig")
        self.assertEqual(used_tokens, 1024)
        self.assertEqual(attempts, [2048, 2048, 2048, 1024])
        self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    def test_inflight_budget_error_is_distinguished_from_hard_provider_errors(self):
        self.assertTrue(is_openrouter_inflight_budget_error(
            'OpenRouter API-fel 402: in_flight_budget_exhausted'
        ))
        self.assertTrue(is_openrouter_budget_error(
            'OpenRouter API-fel 402: in_flight_budget_exhausted'
        ))
        self.assertFalse(is_openrouter_inflight_budget_error(
            'OpenRouter API-fel 402: weight_exceeds_budget'
        ))
        self.assertFalse(is_openrouter_inflight_budget_error(
            'OpenRouter API-fel 401: unauthorized'
        ))

    def test_retries_budget_402_with_smaller_output_cap(self):
        attempts = []

        def fake_ask(message, system_prompt, max_tokens, json_mode, image_data):
            attempts.append(max_tokens)
            if max_tokens > 1024:
                raise ValueError(
                    'OpenRouter API-fel 402: {"metadata":{"reason":"weight_exceeds_budget"}}'
                )
            return "Svar inom återstående kreditbudget"

        answer, used_tokens = run_openrouter_with_budget_fallback(
            fake_ask, "fråga", "system", 8192
        )
        self.assertEqual(answer, "Svar inom återstående kreditbudget")
        self.assertEqual(used_tokens, 1024)
        self.assertEqual(attempts, [8192, 2048, 1024])

    def test_does_not_retry_auth_or_provider_errors(self):
        attempts = []

        def fake_ask(message, system_prompt, max_tokens, json_mode, image_data):
            attempts.append(max_tokens)
            raise ValueError("OpenRouter API-fel 401: invalid API key")

        with self.assertRaisesRegex(ValueError, "401"):
            run_openrouter_with_budget_fallback(
                fake_ask, "fråga", "system", 8192
            )
        self.assertEqual(attempts, [8192])

    def test_stops_after_smallest_budget_if_credits_are_still_insufficient(self):
        attempts = []

        def fake_ask(message, system_prompt, max_tokens, json_mode, image_data):
            attempts.append(max_tokens)
            raise ValueError(
                'OpenRouter API-fel 402: {"metadata":{"reason":"weight_exceeds_budget"}}'
            )

        with self.assertRaisesRegex(ValueError, "402"):
            run_openrouter_with_budget_fallback(
                fake_ask, "fråga", "system", 2048
            )
        self.assertEqual(attempts, [2048, 1024, 512])

    def test_budget_error_detection_is_specific(self):
        self.assertTrue(is_openrouter_budget_error(
            'OpenRouter API-fel 402: maximum cost exceeds your available credits'
        ))
        self.assertFalse(is_openrouter_budget_error(
            'OpenRouter API-fel 401: unauthorized'
        ))
        self.assertFalse(is_openrouter_budget_error(
            'OpenRouter API-fel 503: provider unavailable'
        ))

    def test_budget_sequence_has_no_duplicate_caps(self):
        attempts = []

        def fake_ask(message, system_prompt, max_tokens, json_mode, image_data):
            attempts.append(max_tokens)
            return "ok"

        answer, used_tokens = run_openrouter_with_budget_fallback(
            fake_ask, "fråga", "system", 1024
        )
        self.assertEqual((answer, used_tokens), ("ok", 1024))
        self.assertEqual(attempts, [1024])


if __name__ == "__main__":
    unittest.main()
