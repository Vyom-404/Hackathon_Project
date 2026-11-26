# Teammate 2 integration contract

These modules accept detector-produced records and do not inspect raw notes or implement PII detection. Expected internal shape:

```python
{
    "record_id": "internal-only",
    "source_file": "internal-only",
    "identity_clues": {
        "names": [], "phones": [], "identifiers": [], "relatives": [],
        "age": None, "location": None
    },
    "medical_data": {},
    "patient_id": None
}
```

Keep this object in memory or in encrypted temporary storage only. Never serialize identity clues to the release, logs, exception text, or plaintext scratch files.

## APIs

- `compare_patients(record1, record2) -> bool`: exact identifier/phone agreement is strong evidence. Fuzzy names link only with a matching relative and age within one year. Name-only evidence remains unlinked; conflicting explicit identifiers veto a match.
- `cluster_records(records) -> list[list[int]]`: clusters refer to input list indices. Singleton records are omitted. The clusterer rejects a merge if any cross-cluster pair has conflicting identifiers/phones.
- `generate_patient_id(patient_cluster, secret=None) -> str`: returns `PSN-XXXXXX`, keyed by `secret` or `RAKSHA_SECRET`. Pass the same assembled cluster and secret on every run. A secret of at least 16 bytes is required. Keep the secret out of files and logs.
- `generalize_record(record, age_band_years=5, location_level="district")`: returns a transformed copy; ages become containing bands, PIN codes are coarsened, fine locations are replaced, and unrelated medical values stay intact.
- `shift_patient_dates(record, secret=None, patient_key=None, max_days=180)`: applies one secret-derived offset to every supported ISO or `DD/MM/YYYY` date in a record. Leave uncertain/unlinked records unchanged by passing no key. Use a stable cluster key across that patient's records to preserve relative intervals.
- `measure_privacy_risk(dataset, quasi_identifiers=..., min_group_size=5)`: returns aggregate k-anonymity diagnostics without row values. `suppress_rare_values(...)` offers a copy-on-write suppression helper; choose fields carefully because suppressing diagnosis can reduce medical utility.
- `encrypt_bytes`, `decrypt_bytes`, and `write_encrypted_temp`: protect short-lived intermediates; delete encrypted temp files as soon as sanitization finishes. Prefer a reviewed AEAD library when the deployment can guarantee it is installed.

## Pipeline order

1. Teammate 1 parses each supported input and returns the internal record plus identity clues.
2. Collect all records; call `cluster_records`. Do not force uncertain singletons into clusters.
3. For each accepted cluster, compute one pseudonym and attach it to each corresponding sanitized record. Keep the mapping from input index to cluster only in memory.
4. Generalize age/location and shift dates using a stable cluster key. Keep exact stay duration and medical values.
5. Run risk measurement on the proposed release; apply suppression/generalization policy and re-check.
6. Emit only sanitized records and the organizer's required locators/pseudonyms. Do not emit this internal contract.

The linkage rules are intentionally conservative and are a baseline. Name transliteration and fuzzy equivalence should be expanded only when backed by reliable normalization and tests; false merges are more damaging than unlinked records. K-anonymity diagnostics do not by themselves prove protection from re-identification.

## Git collaboration

Each teammate should work on a named branch. Commit only that teammate's files, push the branch, and open a pull request into shared `main`. Review the diff, resolve conflicts in the shared pipeline together, then merge the PR. Avoid both teammates editing the same integration file at once; coordinate the record contract first. After merging both branches, run the organizer's `validate_output.py` and `check_dev.py` from the toolkit against the integrated pipeline.
