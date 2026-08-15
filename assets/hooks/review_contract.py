#!/usr/bin/env python3
"""Shared content-addressed review-contract helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

REQUEST_SCHEMA = "agentic.review-request/v1"
VERDICT_SCHEMA = "agentic.review-verdict/v1"
DISPOSITIONS = {"PASS", "FAIL", "BLOCKED"}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value: dict[str, Any], digest_field: str) -> str:
    payload = {key: item for key, item in value.items() if key != digest_field}
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


def file_digest(path: Path) -> str:
    if path.is_symlink():
        return hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def valid_project_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def validate_request(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["request must be an object"]
    required = {
        "schema",
        "task_id",
        "round",
        "producer_id",
        "reviewer_id",
        "original_intent",
        "acceptance_criteria",
        "ground_truth",
        "risk_threshold",
        "stop_condition",
        "max_rounds",
        "out_of_scope",
        "files",
        "created_at",
        "request_digest",
    }
    extra = set(value) - required
    missing = required - set(value)
    if extra:
        errors.append(f"unknown request fields: {sorted(extra)}")
    if missing:
        errors.append(f"missing request fields: {sorted(missing)}")
    if value.get("schema") != REQUEST_SCHEMA:
        errors.append("unsupported request schema")
    round_value = value.get("round")
    max_rounds = value.get("max_rounds")
    if (
        not isinstance(round_value, int)
        or isinstance(round_value, bool)
        or round_value < 1
    ):
        errors.append("round must be a positive integer")
    if (
        not isinstance(max_rounds, int)
        or isinstance(max_rounds, bool)
        or not 1 <= max_rounds <= 2
    ):
        errors.append("max_rounds must be an integer from 1 to 2")
    if (
        isinstance(round_value, int)
        and not isinstance(round_value, bool)
        and isinstance(max_rounds, int)
        and not isinstance(max_rounds, bool)
        and round_value > max_rounds
    ):
        errors.append("round cannot exceed max_rounds")
    for field in ("task_id", "producer_id", "reviewer_id", "original_intent", "stop_condition"):
        if not isinstance(value.get(field), str) or not value.get(field):
            errors.append(f"{field} must be a non-empty string")
    criteria = value.get("acceptance_criteria")
    if (
        not isinstance(criteria, list)
        or not criteria
        or any(not isinstance(item, str) or not item for item in criteria)
    ):
        errors.append("acceptance_criteria must be a non-empty list of strings")
    out_of_scope = value.get("out_of_scope")
    if not isinstance(out_of_scope, list) or any(
        not isinstance(item, str) or not item for item in out_of_scope
    ):
        errors.append("out_of_scope must be a list of non-empty strings")
    if not isinstance(value.get("files"), list) or not value.get("files"):
        errors.append("files must be a non-empty list")
    if value.get("producer_id") == value.get("reviewer_id"):
        errors.append("producer and reviewer must differ")
    if value.get("ground_truth") not in {"mechanical", "documentary", "judgment"}:
        errors.append("invalid ground_truth")
    if value.get("risk_threshold") not in {"critical", "high", "medium"}:
        errors.append("invalid risk_threshold")
    files = value.get("files") if isinstance(value.get("files"), list) else []
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            errors.append("every file must contain exactly path and sha256")
            continue
        if not valid_project_path(item["path"]):
            errors.append("file path must be a safe project-relative POSIX path")
        if item["sha256"] is not None and not (
            isinstance(item["sha256"], str) and SHA256_RE.fullmatch(item["sha256"])
        ):
            errors.append("sha256 must be 64 lowercase hexadecimal characters or null")
        if item.get("path") in seen:
            errors.append(f"duplicate file path {item.get('path')!r}")
        seen.add(item.get("path"))
    if not valid_timestamp(value.get("created_at")):
        errors.append("created_at must be a timezone-aware ISO 8601 timestamp")
    if not isinstance(value.get("request_digest"), str) or not DIGEST_RE.fullmatch(
        value["request_digest"]
    ):
        errors.append("request_digest must be a sha256 digest")
    expected = digest(value, "request_digest")
    if value.get("request_digest") != expected:
        errors.append("request_digest does not match request content")
    return errors


def validate_verdict(value: Any, request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["verdict must be an object"]
    required = {
        "schema",
        "task_id",
        "round",
        "request_digest",
        "reviewer_id",
        "disposition",
        "findings",
        "checked_clean",
        "checked_files",
        "stop_condition_met",
        "created_at",
        "verdict_digest",
    }
    extra = set(value) - required
    missing = required - set(value)
    if extra:
        errors.append(f"unknown verdict fields: {sorted(extra)}")
    if missing:
        errors.append(f"missing verdict fields: {sorted(missing)}")
    if value.get("schema") != VERDICT_SCHEMA:
        errors.append("unsupported verdict schema")
    for field in ("task_id", "round", "request_digest", "reviewer_id"):
        if value.get(field) != request.get(field):
            errors.append(f"{field} does not match the request")
    if value.get("disposition") not in DISPOSITIONS:
        errors.append("invalid disposition")
    findings = value.get("findings")
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        errors.append("findings must be a list of objects")
    checked_clean = value.get("checked_clean")
    if not isinstance(checked_clean, list) or any(
        not isinstance(item, str) or not item for item in checked_clean
    ):
        errors.append("checked_clean must be a list of non-empty strings")
    if not isinstance(value.get("checked_files"), list):
        errors.append("checked_files must be a list")
    elif value.get("checked_files") != request.get("files"):
        errors.append("checked_files must exactly match the request file hashes")
    if not isinstance(value.get("stop_condition_met"), bool):
        errors.append("stop_condition_met must be boolean")
    if value.get("reviewer_id") == request.get("producer_id"):
        errors.append("producer cannot sign the verdict")
    if not valid_timestamp(value.get("created_at")):
        errors.append("created_at must be a timezone-aware ISO 8601 timestamp")
    if not isinstance(value.get("verdict_digest"), str) or not DIGEST_RE.fullmatch(
        value["verdict_digest"]
    ):
        errors.append("verdict_digest must be a sha256 digest")
    expected = digest(value, "verdict_digest")
    if value.get("verdict_digest") != expected:
        errors.append("verdict_digest does not match verdict content")
    return errors
