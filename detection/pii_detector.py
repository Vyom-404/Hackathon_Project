from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DetectionSpan:
    entity_type: str
    start: int
    end: int


PHONE_RE = re.compile(
    r"(?<!\d)(?:\+91[\s-]*)?(?:0[\s-]*)?(?:[6-9]\d{9}|[6-9]\d{4}[\s-]?\d{5})(?!\d)"
)
AADHAAR_RE = re.compile(r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)")
ABHA_RE = re.compile(r"(?<!\d)(?:\d[\s-]*){14}(?!\d)")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
MRN_RE = re.compile(r"\b(?:UHID|MRN|HOSPITAL\s*(?:ID|NO\.?))[\s:=#-]*[A-Z]{0,4}[/\-]?\d{4,12}\b", re.IGNORECASE)
INSURANCE_RE = re.compile(r"\b(?:INSURANCE(?:\s*ID)?|POLICY(?:\s*(?:NO|NUMBER))?|CLAIM)\s*[:#-]*\s*[A-Z0-9][A-Z0-9\/\-]{5,18}\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9.!$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+(?![\w.-])", re.IGNORECASE)

LABEL_PATIENT = re.compile(
    r"(?ix)\b(?:patient|pt\.?|name|नाम|रोगी|mareez|mr|mrs|ms|smt\.?|shri|श्री)\b\s*(?:of)?\s*[:=\-]?\s*",
)
RELATIVE_LABEL = re.compile(r"(?ix)\b(?:S/?[oO]|D/?[oO]|W/?[oO]|C/?[oO])\b\s*[:.]?\s*", re.IGNORECASE)
ADDRESS_LABEL = re.compile(r"(?ix)\b(?:address|addr|गिरोह|पता|हाउस|H\.?No\.?|ward|mohalla|tehsil|dist(?:t)?\.?|village)\b\s*[:=\-]?\s*", re.IGNORECASE)
DOB_LABEL = re.compile(r"(?ix)\b(?:dob|date\s*of\s*birth|birth\s*date|जन्म\s*तिथि)\b\s*[:=\-]?\s*", re.IGNORECASE)
HONORIFIC_RE = re.compile(r"(?iu)\b(?:ji|sahab|didi|श्री|जी|साहब|दीदी)\b", re.IGNORECASE)

MEDICAL_CONTEXT = re.compile(
    r"(?ix)\b(?:dolo|paracetamol|ramipril|mg|mcg|ml|mg/dl|mmol|bp|b[p]?|dose|"
    r"disease|syndrome|diagnosis|fever|cough|pain|tab(?:let)?|bd|od|tds|qds|"
    r"hb|hba1c|wbc|rbc|platelets|creatinine|cholesterol|glucose|sugar|"
    r"admission|discharge|follow[- ]?up|x\s+\d+\s+days|days?|hours?|weeks?|"
    r"dr(?:\.|\b))",
)

DOCTOR_RE = re.compile(r"(?iu)\b(?:dr\.?|doctor)\s+[^\n,;|]+", re.IGNORECASE)
KNOWN_MEDICINES_RE = re.compile(r"(?iu)\b(?:dolo\s*650|ramipril(?:\s+\d+(?:\.\d+)?)?\s*(?:mg)?|paracetamol(?:\s+\d+\s*mg)?)\b", re.IGNORECASE)
DATE_RE = re.compile(
    r"(?<!\d)(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{2,4})(?!\d)",
    re.IGNORECASE,
)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _add_span(spans: list[DetectionSpan], entity_type: str, start: int, end: int) -> None:
    if end > start:
        spans.append(DetectionSpan(entity_type, start, end))


def _line_end(text: str, start: int) -> int:
    pos = text.find("\n", start)
    return len(text) if pos < 0 else pos


def _merge_regex(spans: list[DetectionSpan], text: str, pattern: re.Pattern[str], entity_type: str) -> None:
    for match in pattern.finditer(text):
        _add_span(spans, entity_type, *match.span())


def _detect_names(text: str, spans: list[DetectionSpan]) -> None:
    doctors = [m.span() for m in DOCTOR_RE.finditer(text)]

    for match in LABEL_PATIENT.finditer(text):
        start = match.end()
        end = min(_line_end(text, start), len(text))
        while end > start and text[end - 1] in " \t\r,;|":
            end -= 1
        segment = text[start:end]
        segment = re.split(r"\b(?:address|phone|aadhaar|abha|pan|mrn|uhid|diagnosis|sex|age)\b|[,;|]", segment, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if segment:
            local_start = start + (segment and text[start:end].find(segment))
            _add_span(spans, "PATIENT_NAME", local_start, local_start + len(segment))

    # Devanagari and Hinglish labels where a real name follows the label.
    for pattern in (
        re.compile(r"(?iu)(?:नाम|रोगी)\s*[:=-]\s*([^,\n;|]+)", re.UNICODE),
        re.compile(r"(?iu)\b(?:mareez|mohammad|mohd|md)\b\s+([^\n,;|]+)", re.IGNORECASE),
    ):
        for match in pattern.finditer(text):
            start, end = match.span(1) if match.lastindex else match.span()
            segment = text[start:end].strip()
            if segment:
                base = text.find(segment, start)
                if base >= 0:
                    _add_span(spans, "PATIENT_NAME", base, base + len(segment))

    for match in re.finditer(
        r"(?iu)\b([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)?)\s+(?:ji|sahab|didi)\b",
        text,
        re.IGNORECASE,
    ):
        if not MEDICAL_CONTEXT.search(match.group(1)):
            _add_span(spans, "PATIENT_NAME", match.start(1), match.end(1))

    for match in RELATIVE_LABEL.finditer(text):
        start = match.end()
        end = min(_line_end(text, start), len(text))
        segment = re.split(r"[,;|\n]", text[start:end], maxsplit=1)[0].strip()
        if segment and not MEDICAL_CONTEXT.search(segment):
            _add_span(spans, "RELATIVE_NAME", start, start + len(segment))

    # Preserve explicit doctor names and medication/diagnosis context.
    for start, end in doctors:
        spans[:] = [span for span in spans if not (start <= span.start and span.end <= end)]


def _detect_addresses(text: str, spans: list[DetectionSpan]) -> None:
    for match in ADDRESS_LABEL.finditer(text):
        start = match.end()
        end = min(_line_end(text, start), len(text))
        segment = text[start:end].strip()
        if segment:
            split = re.split(r"\b(?:phone|aadhaar|abha|pan|mrn|uhid)\b", segment, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if split:
                local = text.find(split, start)
                _add_span(spans, "ADDRESS", local, local + len(split))


def _detect_dob(text: str, spans: list[DetectionSpan]) -> None:
    for match in DOB_LABEL.finditer(text):
        start = match.end()
        segment = text[start:_line_end(text, start)].strip()
        date_match = DATE_RE.search(segment)
        if date_match:
            absolute = start + date_match.start()
            _add_span(spans, "DOB", absolute, absolute + len(date_match.group(0)))


def detect_pii(text: str) -> list[DetectionSpan]:
    """Detect PII spans in English, Hindi (Devanagari), or Hinglish text.

    Positions are offsets into the NFC-normalized representation. Empty and
    non-string inputs return no spans.
    """
    if not isinstance(text, str) or not text:
        return []

    normalized = _nfc(text)
    spans: list[DetectionSpan] = []

    _merge_regex(spans, normalized, PHONE_RE, "PHONE")
    _merge_regex(spans, normalized, AADHAAR_RE, "AADHAAR")
    _merge_regex(spans, normalized, ABHA_RE, "ABHA")
    _merge_regex(spans, normalized, PAN_RE, "PAN")
    _merge_regex(spans, normalized, MRN_RE, "MRN")
    _merge_regex(spans, normalized, INSURANCE_RE, "INSURANCE_ID")
    _merge_regex(spans, normalized, EMAIL_RE, "EMAIL")

    _detect_names(normalized, spans)
    _detect_addresses(normalized, spans)
    _detect_dob(normalized, spans)

    # Exact character offsets; do not emit nested or overlapping spans.
    spans.sort(key=lambda span: (span.start, -(span.end - span.start)))
    merged: list[DetectionSpan] = []
    for span in spans:
        if not merged:
            merged.append(span)
            continue
        previous = merged[-1]
        if span.start <= previous.end:
            if span.end > previous.end:
                merged[-1] = DetectionSpan(previous.entity_type, previous.start, span.end)
        else:
            merged.append(span)
    return merged
