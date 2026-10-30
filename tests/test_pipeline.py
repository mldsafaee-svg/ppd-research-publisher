import unittest
from pipeline import normalize_doi, eligible, format_message, relevant_title, valid_year, catalogue_record, source_key, merge_candidate

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

    def test_catalogue_record_preserves_evidence_level(self):
        record = catalogue_record({'id':'PPD-1','title':'Postpartum depression among rural mothers','doi':'10.1/test','url':'https://doi.org/10.1/test','year':2025,'source_access':'metadata_only'})
        self.assertEqual(record['evidence_level'], 'metadata_only')
        self.assertEqual(record['publication_status'], 'not_approved')
        self.assertIn('متن کامل', record['note_fa'])

    def test_deduplicate_across_databases(self):
        old={'id':'PPD-1','doi':'10.1234/abc','title':'Postpartum depression','discovered_via':['crossref'],'status':'approved','summary_fa':'تأیید شده'}
        new={'doi':'https://doi.org/10.1234/ABC','title':'Postpartum depression','discovered_via':['openalex'],'abstract_en':'Abstract'}
        merged=merge_candidate(old,new)
        self.assertEqual(source_key(old),source_key(new))
        self.assertEqual(merged['status'],'approved')
        self.assertEqual(merged['summary_fa'],'تأیید شده')
        self.assertEqual(set(merged['discovered_via']),{'crossref','openalex'})
        self.assertEqual(merged['abstract_en'],'Abstract')

    def test_message_contains_source_and_disclaimer(self):
        msg = format_message({"id": "PPD-1", "title": "Test", "url": "https://example.org",
                              "summary_fa": "خلاصه", "limitations_fa": "محدودیت"})
        self.assertIn("https://example.org", msg)
        self.assertIn("محدودیت", msg)
        self.assertIn("PPD-1", msg)

if __name__ == "__main__":
    unittest.main()
