import unittest
from copy import deepcopy

from detection.structured_cleaner import clean_structured_record


class StructuredCleanerTests(unittest.TestCase):
    def test_nested_cleaning_does_not_mutate(self):
        source = {
            "visits": [
                {"patient_name": "Mohammad Arif", "phone": "9876543210", "diagnosis": "Dengue"}
            ]
        }
        original = deepcopy(source)
        cleaned = clean_structured_record(source)
        self.assertEqual(source, original)
        self.assertNotIn("Mohammad Arif", str(cleaned))
        self.assertNotIn("9876543210", str(cleaned))
        self.assertIn("Dengue", str(cleaned))

    def test_sensitive_keys_and_fhir(self):
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"fullUrl": "Patient/p1", "resource": {
                    "resourceType": "Patient",
                    "id": "p1",
                    "name": [{"text": "Mohammad Arif"}],
                    "identifier": [{"system": "aadhaar", "value": "397205839628"}],
                }}
            ],
        }
        cleaned = clean_structured_record(bundle)
        self.assertEqual(cleaned["resourceType"], "Bundle")
        self.assertEqual(cleaned["entry"][0]["resource"]["resourceType"], "Patient")
        self.assertNotIn("397205839628", str(cleaned))
        self.assertNotIn("Mohammad Arif", str(cleaned))


if __name__ == "__main__":
    unittest.main()
