from __future__ import annotations

import copy
import re
from typing import Any

from .transliteration import clean_text


SENSITIVE_KEY_TERMS = (
    "patient", "name", "name_", "phone", "mobile", "contact", "aadhaar",
    "aadhar", "abha", "pan", "mrn", "uhid", "insurance", "policy",
    "address", "addr", "dob", "birth", "relative", "father", "mother",
    "spouse", "guardian", "email",
)

STRUCTURAL_FHIR_KEYS = {
    "resourceType", "id", "meta", "identifier", "reference", "display",
    "type", "system", "value", "use", "text", "status", "period",
    "fullUrl", "entry", "resource", "Bundle",
}


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower().replace("-", "_").replace(" ", "_")
    if key in STRUCTURAL_FHIR_KEYS:
        return lower in {"id", "display", "reference", "value", "text"}
    return any(term in lower for term in SENSITIVE_KEY_TERMS)


def clean_structured_record(record: Any) -> Any:
    """Deep-clean nested dictionaries/lists without mutating the input.

    FHIR structural keys remain present. Sensitive FHIR fields such as
    Patient.identifier.value and Practitioner.display are cleaned conservatively.
    """
    if isinstance(record, dict):
        cleaned: dict[Any, Any] = {}
        for key, value in record.items():
            if not isinstance(key, str):
                cleaned[copy.deepcopy(key)] = clean_structured_record(value)
                continue

            cleaned_key = clean_text(key)
            if isinstance(value, str):
                if key in {"resourceType", "fullUrl"}:
                    cleaned[cleaned_key] = value
                elif key == "reference":
                    cleaned[cleaned_key] = _clean_reference(value)
                elif "doctor" in key.lower():
                    cleaned[cleaned_key] = value
                elif any(term in key.lower() for term in ("patient_name", "relative_name", "father_name", "mother_name", "guardian_name", "spouse_name")):
                    cleaned[cleaned_key] = "[RELATIVE]" if "relative" in key.lower() or "father" in key.lower() or "mother" in key.lower() or "guardian" in key.lower() or "spouse" in key.lower() else "[NAME]"
                elif "name" in key.lower():
                    cleaned[cleaned_key] = "[NAME]"
                elif "patient" in key.lower():
                    cleaned[cleaned_key] = "[NAME]"
                elif any(term in key.lower() for term in ("relative", "father", "mother", "guardian", "spouse")):
                    cleaned[cleaned_key] = "[RELATIVE]"
                elif any(term in key.lower() for term in ("address", "village", "mohalla", "locality", "landmark", "pin")):
                    cleaned[cleaned_key] = "[ADDRESS]"
                elif any(term in key.lower() for term in ("phone", "mobile", "contact")):
                    cleaned[cleaned_key] = "[PHONE]" if value.strip() else value
                elif any(term in key.lower() for term in ("aadhaar", "aadhar", "abha", "pan", "uhid", "mrn", "insurance", "policy")):
                    cleaned[cleaned_key] = "[IDENTIFIER]"
                elif any(term in key.lower() for term in ("dob", "date_of_birth", "birth_date")):
                    cleaned[cleaned_key] = "[DOB]"
                elif _is_sensitive_key(key):
                    cleaned[cleaned_key] = clean_text(value)
                else:
                    cleaned[cleaned_key] = clean_text(value)
            else:
                cleaned[cleaned_key] = clean_structured_record(value)
        return cleaned
    if isinstance(record, list):
        return [clean_structured_record(value) for value in record]
    if isinstance(record, tuple):
        return tuple(clean_structured_record(value) for value in record)
    if isinstance(record, str):
        return clean_text(record)
    return copy.deepcopy(record)


def clean_tabular_row(headers: list[str], row: list[str]) -> list[str]:
    """Clean a CSV/TSV row using header semantics, preserving non-PII columns."""
    cleaned: list[str] = []
    for header, value in zip(headers, row):
        lower = header.lower().replace("-", "_").replace(" ", "_")
        if not isinstance(value, str):
            cleaned.append(copy.deepcopy(value))
            continue

        if any(term in lower for term in (
            "patient_name", "name", "relative", "father", "mother",
            "spouse", "guardian", "subject",
        )) and not any(term in lower for term in ("medication", "doctor", "diagnosis")):
            cleaned.append("[NAME]" if value.strip() else value)
        elif any(term in lower for term in ("mobile", "phone", "contact", "telephone")):
            cleaned.append(clean_text(value))
        elif any(term in lower for term in ("aadhaar", "aadhar", "abha", "pan", "uhid", "mrn", "insurance", "policy")):
            if "mrn" in lower or "uhid" in lower:
                cleaned.append("[MRN]" if value.strip() else value)
            elif "insurance" in lower or "policy" in lower:
                cleaned.append("[INSURANCE_ID]" if value.strip() else value)
            elif "aadhaar" in lower or "aadhar" in lower:
                cleaned.append("[AADHAAR]" if value.strip() else value)
            else:
                cleaned.append(clean_text(value))
        elif any(term in lower for term in ("address", "village", "mohalla", "locality", "landmark", "pin", "postal")):
            cleaned.append("[PIN]" if lower in {"pin", "pin_code", "pincode"} else "[ADDRESS]")
        elif any(term in lower for term in ("dob", "date_of_birth", "birth_date")):
            cleaned.append("[DOB]" if value.strip() else value)
        else:
            cleaned.append(clean_text(value))
    if len(row) > len(headers):
        cleaned.extend(clean_text(copy.deepcopy(value)) if isinstance(value, str) else copy.deepcopy(value) for value in row[len(headers):])
    return cleaned


def sanitize_filename(filename: str) -> str:
    """Replace detected PII in a filename and preserve the file extension."""
    if not isinstance(filename, str):
        return filename
    path_parts = filename.replace("\\", "/").split("/")
    basename = path_parts[-1]
    name, dot, extension = basename.rpartition(".")
    if not dot:
        name = basename
        extension = ""

    cleaned_name = clean_text(name)
    cleaned_name = re.sub(r"\b\d{10,14}\b", "[IDENTIFIER]", cleaned_name)
    cleaned_name = re.sub(r"[^\w.-]+", "_", cleaned_name, flags=re.UNICODE)
    cleaned_name = re.sub(r"_+", "_", cleaned_name).strip("._")
    if not cleaned_name:
        cleaned_name = "sanitized_file"
    path_parts[-1] = cleaned_name + (dot + extension if extension else "")
    return "/".join(path_parts)


def _clean_reference(reference: str) -> str:
    if not isinstance(reference, str):
        return reference
    prefix, separator, tail = reference.partition("/")
    if separator and prefix in {"Patient", "Practitioner", "RelatedPerson", "Person"}:
        cleaned_tail = clean_text(tail)
        if cleaned_tail == tail:
            return reference
        return f"{prefix}/{cleaned_tail}"
    return clean_text(reference)
