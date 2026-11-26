import unittest

from detection.pii_detector import detect_pii
from detection.transliteration import clean_text


class PiiDetectorTests(unittest.TestCase):
    def test_english_identifier_detection(self):
        text = "Patient: Mohammad Arif, Phone: 9876543210, Aadhaar: 3972 0583 9628"
        spans = detect_pii(text)
        kinds = {span.entity_type for span in spans}
        self.assertIn("PHONE", kinds)
        self.assertIn("AADHAAR", kinds)
        self.assertIn("PATIENT_NAME", kinds)

    def test_medical_values_are_preserved(self):
        text = "Patient: Mohammad Arif; Phone: 9876543210; Diagnosis: Dengue; BP: 150/90; Medicine: Dolo 650 BD x 5 days"
        cleaned = clean_text(text)
        self.assertNotIn("Mohammad Arif", cleaned)
        self.assertNotIn("9876543210", cleaned)
        self.assertIn("Dengue", cleaned)
        self.assertIn("BP: 150/90", cleaned)
        self.assertIn("Dolo 650 BD x 5 days", cleaned)

    def test_hindi_and_hinglish_detection(self):
        hindi = "नाम: मोहम्मद शाहिद फोन: 98765-43210"
        hinglish = "Shahid sahab ka BP 117/82 aur phone +91 98765 43210"
        for text in (hindi, hinglish):
            self.assertTrue(detect_pii(text))

    def test_co_relative_vs_complaint(self):
        relative = "C/O Zubair"
        complaint = "C/O fever"
        relative_spans = detect_pii(relative)
        complaint_spans = detect_pii(complaint)
        self.assertTrue(any(s.entity_type == "RELATIVE_NAME" for s in relative_spans))
        self.assertFalse(any(s.entity_type == "RELATIVE_NAME" for s in complaint_spans))

    def test_doctor_name_preserved(self):
        cleaned = clean_text("Dr. Ramesh prescribed Ramipril 5 mg")
        self.assertIn("Dr. Ramesh", cleaned)
        self.assertIn("Ramipril 5 mg", cleaned)

    def test_malformed_and_empty(self):
        self.assertEqual(detect_pii(""), [])
        self.assertEqual(detect_pii(None), [])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
