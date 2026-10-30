import unittest
from pipeline import normalize_doi, eligible, format_message, relevant_title, valid_year

class PipelineTests(unittest.TestCase):
    def test_normalize_doi(self):
        self.assertEqual(normalize_doi("https://doi.org/10.1234/ABC"), "10.1234/abc")
    def test_eligible_requires_source_and_review(self):
        self.assertFalse(eligible({"status": "approved", "title": "X"}))
        self.assertFalse(eligible({"status": "draft", "title": "X", "url": "https://example.org"}))
        self.assertTrue(eligible({"status": "approved", "title": "X", "url": "https://example.org", "summary_fa": "متن"}))
    def test_discovery_rejects_irrelevant_titles_and_invalid_years(self):
        self.assertFalse(relevant_title('Buying behavior during economic depression'))
        self.assertTrue(relevant_title('Postpartum depression among rural mothers'))
        self.assertFalse(valid_year(2116))
        self.assertTrue(valid_year(2025))

    def test_message_contains_source_and_disclaimer(self):
        msg = format_message({"id": "PPD-1", "title": "Test", "url": "https://example.org",
                              "summary_fa": "خلاصه", "limitations_fa": "محدودیت"})
        self.assertIn("https://example.org", msg)
        self.assertIn("محدودیت", msg)
        self.assertIn("PPD-1", msg)

if __name__ == "__main__":
    unittest.main()
