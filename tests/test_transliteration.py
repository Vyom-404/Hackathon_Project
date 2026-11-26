import unittest

from detection.transliteration import normalize_name


class TransliterationTests(unittest.TestCase):
    def test_initials_punctuation_and_honorific(self):
        self.assertEqual(normalize_name("  A. K. Sharma ji  "), normalize_name("A K Sharma"))

    def test_devanagari_name_normalized(self):
        normalized = normalize_name("मोहम्मद शाहिद")
        self.assertIn("mohammad", normalized)


if __name__ == "__main__":
    unittest.main()
