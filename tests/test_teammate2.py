import tempfile
import unittest
from pathlib import Path

from linkage.pseudonymization import generate_patient_id
from linkage.record_linkage import compare_patients, cluster_records
from privacy.date_shifting import date_shift_days, shift_patient_dates
from privacy.generalization import generalize_record
from privacy.risk_detection import measure_privacy_risk, suppress_rare_values
from privacy.secure_storage import decrypt_bytes, encrypt_bytes, write_encrypted_temp

SECRET = "test-secret-at-least-16-bytes"


class LinkageTests(unittest.TestCase):
    def test_same_phone_links_and_conflicting_identifier_vetoes(self):
        a = {"identity_clues": {"names": ["Asha Devi"], "phones": ["+91 98765 43210"], "identifiers": ["MRN-A"]}}
        b = {"identity_clues": {"names": ["Asha Devi"], "phones": ["9876543210"], "identifiers": ["MRN-A"]}}
        c = {"identity_clues": {"names": ["Asha Devi"], "phones": ["9876543210"], "identifiers": ["MRN-C"]}}
        self.assertTrue(compare_patients(a, b))
        self.assertFalse(compare_patients(a, c))

    def test_name_only_does_not_link(self):
        a = {"names": ["Ravi Kumar"], "age": 40}
        b = {"names": ["Ravi Kumar"], "age": 40}
        self.assertFalse(compare_patients(a, b))

    def test_cluster_rejects_transitive_identifier_conflict(self):
        rows = [
            {"identifiers": ["id-001"], "phones": ["9876543210"]},
            {"identifiers": ["id-001"], "phones": ["9876543210"]},
            {"identifiers": ["id-002"], "phones": ["9876543210"]},
        ]
        self.assertEqual(cluster_records(rows), [[0, 1]])


class PrivacyTests(unittest.TestCase):
    def test_pseudonym_is_stable_and_secret_dependent(self):
        cluster = [{"identifiers": ["MRN-42"]}]
        self.assertEqual(generate_patient_id(cluster, SECRET), generate_patient_id(cluster, SECRET))
        self.assertNotEqual(generate_patient_id(cluster, SECRET), generate_patient_id(cluster, "another-secret-at-least-16"))

    def test_shift_is_consistent_and_preserves_stay_length(self):
        record = {"admit": "2026-05-01", "discharge": "2026-05-10", "note": "BP 120/80"}
        shifted = shift_patient_dates(record, SECRET, "patient-key")
        self.assertEqual(shifted["note"], record["note"])
        self.assertEqual(date_shift_days("patient-key", SECRET), date_shift_days("patient-key", SECRET))
        from datetime import date
        before = date.fromisoformat(record["discharge"]) - date.fromisoformat(record["admit"])
        after = date.fromisoformat(shifted["discharge"]) - date.fromisoformat(shifted["admit"])
        self.assertEqual(before, after)

    def test_generalization_keeps_medical_values(self):
        row = {"age": 48, "PIN": "229073", "diagnosis": "Parkinson's disease", "dose": "Dolo 650"}
        result = generalize_record(row)
        self.assertEqual(result["age"], "45-49")
        self.assertEqual(result["PIN"], "229**")
        self.assertEqual(result["diagnosis"], row["diagnosis"])
        self.assertEqual(result["dose"], row["dose"])

    def test_risk_measurement_and_suppression(self):
        data = [{"age_band": "40-44", "gender": "F"}, {"age_band": "40-44", "gender": "F"},
                {"age_band": "80-84", "gender": "M"}]
        risk = measure_privacy_risk(data, ("age_band", "gender"), 2)
        self.assertEqual(risk["records_below_k"], 1)
        self.assertEqual(suppress_rare_values(data, ("age_band", "gender"), 2)[2]["age_band"], "[SUPPRESSED]")

    def test_authenticated_encryption_roundtrip(self):
        plain = b"sensitive intermediate"
        blob = encrypt_bytes(plain, SECRET)
        self.assertNotIn(plain, blob)
        self.assertEqual(decrypt_bytes(blob, SECRET), plain)
        tampered = bytearray(blob)
        tampered[-1] ^= 1
        with self.assertRaises(ValueError):
            decrypt_bytes(bytes(tampered), SECRET)
        with tempfile.TemporaryDirectory() as d:
            path = write_encrypted_temp(plain, SECRET, d)
            self.assertEqual(decrypt_bytes(path.read_bytes(), SECRET), plain)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
