import unittest

from detection.name_detector import extract_identity_clues
from detection.pii_detector import detect_pii
from detection.transliteration import normalize_name


class NameDetectorTests(unittest.TestCase):
    def test_name_normalization_variants(self):
        self.assertEqual(normalize_name("Mohammad   Arif"), normalize_name("Mohd. Arif"))
        self.assertEqual(normalize_name("Dr. Mohd. Shahid ji"), normalize_name("Mohammad Shahid"))

    def test_nested_clues(self):
        record = {
            "patient_name": "Mohammad Arif",
            "phone": "9876543210",
            "nested": [{"mrn": "UHID-123456"}, {"relative": "S/o Zubair"}],
        }
        clues = extract_identity_clues(record)
        self.assertIn("9876543210", clues["phones"])
        self.assertTrue(clues["identifiers"])

    def test_no_identity_leak_in_span_value(self):
        spans = detect_pii("Patient: Mohammad Arif")
        self.assertTrue(spans)
        self.assertTrue(all(hasattr(span, "start") and hasattr(span, "end") for span in spans))


if __name__ == "__main__":
    unittest.main()
