# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
import datetime
import hashlib
import json
import re

from genlayer import *


OUTCOMES = ("CONSISTENT", "CONFLICTING", "MISSING_VERSION", "UNRESOLVED")
STATES = ("DRAFT", "FROZEN", "RETRYING", "ASSESSED")
MAX_BODY = 120_000
MAX_TEXT = 256
MAX_URL = 2_048
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@allow_storage
@dataclass
class CaseRecord:
    owner: Address
    subject_id: str
    url_a: str
    url_b: str
    notice_id_a: str
    notice_id_b: str
    revision_a: str
    revision_b: str
    effective_date_a: str
    effective_date_b: str
    retrieved_not_before: str
    retrieved_not_after: str
    state: str
    outcome: str
    digest_a: str
    digest_b: str
    retry_count: u8


def _fail(message: str) -> None:
    raise gl.vm.UserError(message)


def _bounded(value: str, label: str, limit: u256) -> str:
    text = str(value).strip()
    if not text or len(text) > limit:
        _fail("invalid " + label)
    return text


def _date(value: str, label: str) -> str:
    text = _bounded(value, label, 10)
    if not DATE_RE.match(text):
        _fail("invalid " + label)
    try:
        datetime.date.fromisoformat(text)
    except Exception:
        _fail("invalid " + label)
    return text


def _https(value: str, label: str) -> str:
    text = _bounded(value, label, MAX_URL)
    if not text.startswith("https://") or any(char.isspace() for char in text):
        _fail("invalid " + label)
    return text


def _text_from_body(body) -> str:
    if isinstance(body, bytes):
        text = body.decode("utf-8")
    else:
        text = str(body)
    if len(text) > MAX_BODY:
        raise ValueError("body too large")
    return text


def _html_field(body: str, name: str) -> str:
    patterns = (
        r"data-" + name + r"\s*=\s*[\"']([^\"']+)[\"']",
        r"name\s*=\s*[\"']" + name + r"[\"'][^>]*content\s*=\s*[\"']([^\"']+)[\"']",
    )
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _header(response, name: str) -> str:
    headers = getattr(response, "headers", {}) or {}
    for key, value in headers.items():
        if str(key).lower() == name:
            if not isinstance(value, str):
                raise ValueError("invalid response header")
            return value.strip()
    return ""


def _header_date(value: str) -> str:
    if len(value) == 10:
        return value
    try:
        date_part = value.split(",", 1)[1].strip().rsplit(" ", 1)[0]
        return datetime.datetime.strptime(date_part, "%d %b %Y %H:%M:%S").date().isoformat()
    except Exception:
        return value


def _source_field(payload: dict, key: str, limit: int) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str):
        raise ValueError("invalid source metadata")
    value = value.strip()
    if len(value) > limit:
        raise ValueError("source metadata too large")
    return value


def _checked_source_value(value, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid source metadata")
    value = value.strip()
    if len(value) > limit:
        raise ValueError("source metadata too large")
    return value


def _extract(response) -> dict:
    status = int(response.status)
    body = _text_from_body(response.body)
    payload = None
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            payload = parsed
    except Exception:
        payload = None

    if payload is not None:
        notice_id = _source_field(payload, "notice_id", MAX_TEXT)
        revision = _source_field(payload, "revision", MAX_TEXT)
        effective_date = _source_field(payload, "effective_date", 10)
        retrieved_at = _source_field(payload, "retrieved_at", 10)
        content = _source_field(payload, "content", MAX_BODY)
    else:
        if not re.search(r"<[^>]+>", body):
            raise ValueError("malformed source")
        notice_id = _checked_source_value(_html_field(body, "notice-id"), MAX_TEXT)
        revision = _checked_source_value(_html_field(body, "revision"), MAX_TEXT)
        effective_date = _checked_source_value(_html_field(body, "effective-date"), 10)
        retrieved_at = _checked_source_value(_html_field(body, "retrieved-at"), 10)
        content = re.sub(r"<[^>]+>", " ", body)
        content = re.sub(r"\s+", " ", content).strip()

    if not retrieved_at:
        retrieved_at = _header(response, "x-source-retrieved-date")
    if not retrieved_at:
        retrieved_at = _header(response, "last-modified")
    if not retrieved_at:
        retrieved_at = _header(response, "date")
    retrieved_at = _header_date(retrieved_at)
    if not retrieved_at or len(retrieved_at) > 10:
        raise ValueError("missing or invalid retrieval timestamp")
    _date(retrieved_at, "source retrieved_at")
    if effective_date:
        _date(effective_date, "source effective_date")
    if len(content) > MAX_BODY:
        raise ValueError("content too large")
    if not content:
        raise ValueError("missing content")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else ""
    return {
        "status": status,
        "notice_id": notice_id,
        "revision": revision,
        "effective_date": effective_date,
        "retrieved_at": retrieved_at,
        "digest": digest,
    }


def _unresolved(reason: str) -> dict:
    return {"outcome": "UNRESOLVED", "digest_a": "", "digest_b": "", "reason": reason}


def _assess_sources(
    url_a: str,
    url_b: str,
    notice_id_a: str,
    notice_id_b: str,
    revision_a: str,
    revision_b: str,
    effective_date_a: str,
    effective_date_b: str,
    retrieved_not_before: str,
    retrieved_not_after: str,
) -> dict:
    try:
        response_a = gl.nondet.web.get(url_a)
        source_a = _extract(response_a)
        response_b = gl.nondet.web.get(url_b)
        source_b = _extract(response_b)
    except Exception:
        return _unresolved("EXTERNAL_FAILURE")

    if source_a["status"] != 200 or source_b["status"] != 200:
        return _unresolved("UNAVAILABLE_SOURCE")
    if not (
        retrieved_not_before <= source_a["retrieved_at"] <= retrieved_not_after
        and retrieved_not_before <= source_b["retrieved_at"] <= retrieved_not_after
    ):
        return _unresolved("RETRIEVAL_OUTSIDE_WINDOW")
    if not source_a["notice_id"] or not source_a["revision"] or not source_a["effective_date"]:
        return {"outcome": "MISSING_VERSION", "digest_a": source_a["digest"], "digest_b": source_b["digest"]}
    if not source_b["notice_id"] or not source_b["revision"] or not source_b["effective_date"]:
        return {"outcome": "MISSING_VERSION", "digest_a": source_a["digest"], "digest_b": source_b["digest"]}

    expected = (
        (source_a, notice_id_a, revision_a, effective_date_a),
        (source_b, notice_id_b, revision_b, effective_date_b),
    )
    for source, expected_id, expected_revision, expected_date in expected:
        if (
            source["notice_id"] != expected_id
            or source["revision"] != expected_revision
            or source["effective_date"] != expected_date
        ):
            return _unresolved("PROVENANCE_MISMATCH")

    outcome = "CONSISTENT" if source_a["digest"] == source_b["digest"] else "CONFLICTING"
    return {
        "outcome": outcome,
        "digest_a": source_a["digest"],
        "digest_b": source_b["digest"],
    }


def _same_decision(left: dict, right: dict) -> bool:
    return (
        isinstance(right, dict)
        and left.get("outcome") == right.get("outcome")
        and left.get("digest_a") == right.get("digest_a")
        and left.get("digest_b") == right.get("digest_b")
    )


class Contract(gl.Contract):
    cases: TreeMap[str, CaseRecord]

    def __init__(self):
        pass

    @gl.public.write
    def create_case(
        self,
        case_id: str,
        subject_id: str,
        url_a: str,
        url_b: str,
        notice_id_a: str,
        notice_id_b: str,
        revision_a: str,
        revision_b: str,
        effective_date_a: str,
        effective_date_b: str,
        retrieved_not_before: str,
        retrieved_not_after: str,
    ) -> None:
        case_id = _bounded(case_id, "case_id", 96)
        subject_id = _bounded(subject_id, "subject_id", MAX_TEXT)
        url_a = _https(url_a, "url_a")
        url_b = _https(url_b, "url_b")
        if url_a == url_b:
            _fail("source URLs must differ")
        notice_id_a = _bounded(notice_id_a, "notice_id_a", MAX_TEXT)
        notice_id_b = _bounded(notice_id_b, "notice_id_b", MAX_TEXT)
        revision_a = _bounded(revision_a, "revision_a", MAX_TEXT)
        revision_b = _bounded(revision_b, "revision_b", MAX_TEXT)
        effective_date_a = _date(effective_date_a, "effective_date_a")
        effective_date_b = _date(effective_date_b, "effective_date_b")
        retrieved_not_before = _date(retrieved_not_before, "retrieved_not_before")
        retrieved_not_after = _date(retrieved_not_after, "retrieved_not_after")
        if retrieved_not_before > retrieved_not_after:
            _fail("invalid retrieval window")
        if case_id in self.cases:
            _fail("case already exists")
        self.cases[case_id] = CaseRecord(
            gl.message.sender_address,
            subject_id,
            url_a,
            url_b,
            notice_id_a,
            notice_id_b,
            revision_a,
            revision_b,
            effective_date_a,
            effective_date_b,
            retrieved_not_before,
            retrieved_not_after,
            "DRAFT",
            "UNRESOLVED",
            "",
            "",
            0,
        )

    @gl.public.write
    def freeze_case(self, case_id: str) -> None:
        record = self.cases[case_id]
        if gl.message.sender_address != record.owner:
            _fail("only the owner can freeze")
        if record.state != "DRAFT":
            _fail("case is not draft")
        record.state = "FROZEN"

    def _assess(self, case_id: str) -> None:
        record = self.cases[case_id]
        url_a = str(record.url_a)
        url_b = str(record.url_b)
        notice_id_a = str(record.notice_id_a)
        notice_id_b = str(record.notice_id_b)
        revision_a = str(record.revision_a)
        revision_b = str(record.revision_b)
        effective_date_a = str(record.effective_date_a)
        effective_date_b = str(record.effective_date_b)
        retrieved_not_before = str(record.retrieved_not_before)
        retrieved_not_after = str(record.retrieved_not_after)

        def leader_fn():
            return _assess_sources(
                url_a,
                url_b,
                notice_id_a,
                notice_id_b,
                revision_a,
                revision_b,
                effective_date_a,
                effective_date_b,
                retrieved_not_before,
                retrieved_not_after,
            )

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_result = _assess_sources(
                    url_a,
                    url_b,
                    notice_id_a,
                    notice_id_b,
                    revision_a,
                    revision_b,
                    effective_date_a,
                    effective_date_b,
                    retrieved_not_before,
                    retrieved_not_after,
                )
                return _same_decision(leader_result.calldata, validator_result)
            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        if not isinstance(result, dict) or result.get("outcome") not in OUTCOMES:
            _fail("invalid consensus result")
        record.digest_a = str(result.get("digest_a", ""))
        record.digest_b = str(result.get("digest_b", ""))
        record.outcome = str(result["outcome"])
        record.state = "ASSESSED"

    @gl.public.write
    def assess(self, case_id: str) -> None:
        record = self.cases[case_id]
        if record.state not in ("FROZEN", "RETRYING"):
            _fail("case is not assessable")
        self._assess(case_id)

    @gl.public.write
    def retry_unresolved(self, case_id: str) -> None:
        record = self.cases[case_id]
        if record.outcome != "UNRESOLVED":
            _fail("case is not unresolved")
        if record.retry_count >= 2:
            _fail("retry limit reached")
        record.retry_count = record.retry_count + 1
        record.state = "RETRYING"
        self._assess(case_id)

    def _record_json(self, record: CaseRecord, result_only: bool) -> str:
        data = {
            "subject_id": str(record.subject_id),
            "state": str(record.state),
            "outcome": str(record.outcome),
            "digest_a": str(record.digest_a),
            "digest_b": str(record.digest_b),
            "retry_count": int(record.retry_count),
        }
        if not result_only:
            data.update(
                {
                    "owner": str(record.owner),
                    "url_a": str(record.url_a),
                    "url_b": str(record.url_b),
                    "notice_id_a": str(record.notice_id_a),
                    "notice_id_b": str(record.notice_id_b),
                    "revision_a": str(record.revision_a),
                    "revision_b": str(record.revision_b),
                    "effective_date_a": str(record.effective_date_a),
                    "effective_date_b": str(record.effective_date_b),
                    "retrieved_not_before": str(record.retrieved_not_before),
                    "retrieved_not_after": str(record.retrieved_not_after),
                }
            )
        return json.dumps(data, sort_keys=True)

    @gl.public.view
    def get_case(self, case_id: str) -> str:
        return self._record_json(self.cases[case_id], False)

    @gl.public.view
    def get_result(self, case_id: str) -> str:
        return self._record_json(self.cases[case_id], True)
