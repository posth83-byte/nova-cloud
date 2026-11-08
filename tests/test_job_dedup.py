import unittest

from job_dedup import (
    normalize_job_task,
    job_task_fingerprint,
    is_duplicate_job_task,
)


class JobDeduplicationTests(unittest.TestCase):
    def test_normalization_ignores_case_punctuation_and_spacing(self):
        self.assertEqual(
            normalize_job_task("  Testa PR #24!!  "),
            normalize_job_task("testa   pr 24")
        )

    def test_fingerprint_is_stable_for_equivalent_text(self):
        self.assertEqual(
            job_task_fingerprint("Kontrollera PR #24"),
            job_task_fingerprint("kontrollera pr 24!")
        )

    def test_substantially_same_test_is_detected(self):
        self.assertTrue(is_duplicate_job_task(
            "Granska PR 24 och testa mobilmenyn, knapparna, formuläret och navigeringen",
            "Granska PR #24: testa mobilmeny, knappar, formulär och navigering igen"
        ))

    def test_unrelated_tasks_are_not_merged(self):
        self.assertFalse(is_duplicate_job_task(
            "Granska PR 24 och testa mobilmenyn, knapparna, formuläret och navigeringen",
            "Kontrollera Kling API-token och videogenerering"
        ))

    def test_short_generic_prompts_are_not_fuzzy_merged(self):
        self.assertFalse(is_duplicate_job_task("testa igen", "testa den igen"))
        self.assertFalse(is_duplicate_job_task("testa igen", "testa igen"))

    def test_different_numeric_identifiers_are_never_merged(self):
        self.assertFalse(is_duplicate_job_task(
            "Granska PR 36 och testa mobilmenyn, knapparna, formuläret och navigeringen",
            "Granska PR 37 och testa mobilmenyn, knapparna, formuläret och navigeringen"
        ))

    def test_negated_and_positive_instructions_are_never_merged(self):
        self.assertFalse(is_duplicate_job_task(
            "Granska PR 36 och ta bort den gamla jobbposten från databasen permanent",
            "Granska PR 36 och ta inte bort den gamla jobbposten från databasen permanent"
        ))

    def test_same_negated_instruction_is_still_detected(self):
        self.assertTrue(is_duplicate_job_task(
            "Granska PR 36 och ta inte bort den gamla jobbposten från databasen permanent",
            "Granska PR 36 och ta inte bort den gamla jobbposten från databasen permanent igen"
        ))


if __name__ == "__main__":
    unittest.main()
