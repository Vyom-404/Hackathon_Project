# Detection Engine Integration

## Scope

The detection package handles text and structured-record PII detection, Indian name
normalization, transliteration normalization, medical-context protection, and cleaning.
It intentionally does not perform linkage, pseudonym generation, date shifting, or
privacy transformations owned by Teammate 2.

## Public API

```python
detect_pii(text: str) -> list[DetectionSpan]
normalize_name(name: str) -> str
extract_identity_clues(record: object) -> dict[str, list[str] | str | None]
clean_text(text: str) -> str
clean_structured_record(record: object) -> object
protect_medical_text(text: str) -> str
is_medical_context(text: str, start: int, end: int) -> bool
```

`DetectionSpan` is a frozen data object containing `entity_type`, `start`, and `end`.
Offsets refer to the original unmodified text in `detect_pii(clean_text)`; cleaning is
performed from right to left by merging spans internally. Detection supports English,
Hindi Devanagari, and Hinglish.

## Teammate 2 workflow

1. Parse the original record using the existing starter I/O code.
2. Call `extract_identity_clues(record)` for each in-memory record.
3. Pass the returned dictionary to linkage logic only in memory.
4. After Teammate 2 resolves a pseudonymous patient ID, call `clean_structured_record`
   for the sanitized copy and insert the resolved ID through the existing pipeline.
5. Teammate 2 must perform its own privacy transformations and write only the final
   validated output.

Example:

```python
from detection import extract_identity_clues, clean_structured_record

clues = extract_identity_clues(record)
# linkage_result = teammate2_link(clues)
cleaned = clean_structured_record(record)
```

Identity clues must not be written to logs, temporary files, reports, or debug output.

## Uncertainty

Ambiguous names and transliterations are normalized but never matched. A record must
retain `null` for patient linkage when evidence is insufficient. Context rules preserve
doctor names, medicines, doses, diagnoses, vital signs, and laboratory values.

## Known limitations

- Name detection is context-driven and may miss names with no label or honorific.
- Transliteration is lightweight and explainable; it does not provide universal Indic
  language conversion.
- Addresses are detected by labels and may require stronger gazetteers for new formats.
- FHIR cleaning preserves structure and structural fields but does not generate or
  validate identifiers or references.
