import unittest

from detection.medical_protection import is_medical_context
from detection.transliteration import clean_text


class MedicalProtectionTests(unittest.TestCase):
    def test_preserves_medical_examples(self):
        text = "Ramipril 5 mg; 1-0-1; BP 150/90; Parkinson's disease; Creatinine 1.2 mg/dL"
        cleaned = clean_text(text)
        for value in ("Ramipril 5 mg", "1-0-1", "BP 150/90", "Parkinson's disease", "Creatinine 1.2 mg/dL"):
            self.assertIn(value, cleaned)

    def test_medical_context_helper(self):
        text = "Prescription: Dolo 650 BD x 5 days"
        self.assertTrue(is_medical_context(text, 13, 21))


if __name__ == "__main__":
    unittest.main()
