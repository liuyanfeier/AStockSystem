"""Verify retained collector evidence, not a manifest's self-reported trust grade.

Local unsigned receipts establish internal capture lineage, not provider authenticity.
The same checks apply to source files and content-addressed Store rebuilds.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from astock.data.raw_validation import strict_json
from astock.research.core import digest, instant, require

if TYPE_CHECKING:
    from astock.research.acquisition import CapturePlan
    from astock.research.inputs import Bundle, SourceFile

CLAIM_KEYS = {"plan_hash", "member", "claimed_at", "approval_hash"}
APPROVAL_KEYS = {"protocol", "plan_hash", "destination", "implementation_hash", "authorized_by",
                 "approved_at", "expires_at", "member_ids", "fixture_only", "execution_authorized"}
CONTINUING_APPROVAL_KEYS = APPROVAL_KEYS | {"continue_on_error"}
RESULT_KEYS = {"member", "claim_hash", "state", "error", "transport", "object", "sha256",
               "retrieved_at", "available_at"}


def validate_authority(plan: CapturePlan, claim: dict, approval: dict) -> str:
    """Validate recorded authority; never grant a new execution license.

    Historical implementation hashes remain historical pins, not the running hash.
    Relocating retained evidence does not alter the recorded execution destination.
    """
    require(set(claim) == CLAIM_KEYS and set(approval) in (APPROVAL_KEYS, CONTINUING_APPROVAL_KEYS), "CAPTURE_AUTHORITY_SHAPE")
    require("continue_on_error" not in approval or type(approval["continue_on_error"]) is bool,
            "CAPTURE_CONTINUATION_POLICY")
    plan_hash = digest(plan.model_dump(mode="json"))
    member_ids = [digest(member) for member in plan.members]
    ids = approval["member_ids"]
    destination = approval["destination"]
    suffix = PurePosixPath(plan.destination)
    require(not suffix.is_absolute() and ".." not in suffix.parts and
            isinstance(destination, str) and PurePosixPath(destination).is_absolute() and
            ".." not in PurePosixPath(destination).parts and
            PurePosixPath(destination).parts[-len(suffix.parts):] == suffix.parts, "CAPTURE_DESTINATION_BINDING")
    require(isinstance(ids, list) and ids and len(ids) == len(set(ids)) and
            ids == [key for key in member_ids if key in ids] and digest(claim["member"]) in ids,
            "CAPTURE_APPROVAL_MEMBERS")
    require(claim["member"] in plan.members and claim["plan_hash"] == plan_hash and
            approval["plan_hash"] == plan_hash and digest(approval) == claim["approval_hash"], "CAPTURE_AUTHORITY_BINDING")
    require(approval["protocol"] == "RESEARCH_CAPTURE_APPROVAL_V1_1" and
            approval["execution_authorized"] is True and type(approval["fixture_only"]) is bool and
            isinstance(approval["implementation_hash"], str) and
            re.fullmatch(r"[0-9a-f]{64}", approval["implementation_hash"]) is not None, "CAPTURE_APPROVAL_CONTRACT")
    fixture = approval["fixture_only"]
    require(approval["authorized_by"] == ("SYNTHETIC_TEST" if fixture else "HUMAN"), "CAPTURE_AUTHORIZER")
    require(instant(approval["approved_at"]) <= instant(claim["claimed_at"]) <= instant(approval["expires_at"]) and
            instant(claim["claimed_at"]) >= instant(plan.not_before), "CAPTURE_AUTHORITY_TIME")
    return "SYNTHETIC" if fixture else "LOCAL_CAPTURE_BOUND"


def capture_grade(spec: SourceFile, body: bytes, bundle: Bundle, proofs: dict[str, bytes] | None) -> str:
    """Return a grade only after checking the complete plan/claim/approval/result/raw chain."""
    if spec.evidence_grade == "USER_DECLARED" or not spec.evidence:
        require(spec.evidence_grade != "LOCAL_CAPTURE_BOUND", "CAPTURE_EVIDENCE_REQUIRED")
        return spec.evidence_grade
    require(spec.adapter == "tushare-response-v1" and len(spec.evidence) == 4 and
            len({p.sha256 for p in spec.evidence}) == 4 and proofs is not None, "CAPTURE_EVIDENCE_REQUIRED")
    values = []
    for proof in spec.evidence:
        value = proofs.get(proof.sha256)
        require(value is not None and hashlib.sha256(value).hexdigest() == proof.sha256, "CAPTURE_EVIDENCE_HASH")
        decoded = strict_json(value)
        require(isinstance(decoded, dict), "CAPTURE_EVIDENCE_SHAPE")
        values.append((value, decoded))
    # Identify roles by their strict schemas, independent of filenames or list order.
    def role(keys: set[str]) -> tuple[bytes, dict]:
        matches = [(raw, value) for raw, value in values if set(value) == keys or
                   keys == APPROVAL_KEYS and set(value) == CONTINUING_APPROVAL_KEYS]
        require(len(matches) == 1, "CAPTURE_EVIDENCE_ROLES")
        return matches[0]
    claim_bytes, claim = role(CLAIM_KEYS)
    _, approval = role(APPROVAL_KEYS)
    _, result = role(RESULT_KEYS)
    plans = [value for _, value in values if value.get("protocol") in {"RESEARCH_CAPTURE_V1_1", "RESEARCH_CAPTURE_V2"}]
    require(len(plans) == 1, "CAPTURE_EVIDENCE_ROLES")
    from astock.research.market_capture import parse_plan
    plan = parse_plan(plans[0])
    grade = validate_authority(plan, claim, approval)
    require(spec.evidence_grade == grade, "CAPTURE_GRADE_MISMATCH")
    require(result["state"] == "COMPLETE" and result["error"] is None and
            result["transport"] == ("MOCK" if grade == "SYNTHETIC" else "HTTPS_TLS") and
            result["member"] == claim["member"] == spec.request and
            result["claim_hash"] == hashlib.sha256(claim_bytes).hexdigest(), "CAPTURE_RECEIPT_BINDING")
    require(result["object"] == f"{digest(spec.request)}.response.json" and
            result["sha256"] == spec.sha256 == hashlib.sha256(body).hexdigest(), "CAPTURE_RAW_BINDING")
    require(spec.source == "Tushare research capture", "CAPTURE_PROVIDER_BINDING")
    require(instant(result["available_at"]) >= instant(result["retrieved_at"]) >= instant(claim["claimed_at"]) and
            instant(spec.retrieved_at) == instant(result["retrieved_at"]) and
            instant(spec.available_at) >= instant(result["available_at"]), "CAPTURE_SOURCE_TIME_BINDING")
    require(bundle.purpose == plan.purpose and bundle.window_start == plan.window_start and
            bundle.window_end == plan.window_end and (bundle.universe == plan.universe if plan.protocol == 'RESEARCH_CAPTURE_V1_1' else
             bundle.protocol == 'RESEARCH_INPUT_V2' and bundle.bse_calendar_reference == plan.bse_calendar_reference and bundle.universe_scope in {'CURRENT_A_SHARE_L', 'PROVIDER_SAMPLE'}) and
            bundle.benchmarks == plan.benchmarks and (plan.protocol == 'RESEARCH_CAPTURE_V2' or bundle.universe_scope == "WATCHLIST"), "CAPTURE_SCOPE_BINDING")
    calendar = plan.benchmark_calendars.get(spec.request["params"].get("ts_code")) if spec.request["api"] == "index_basic" else None
    require(spec.calendar_exchange == calendar, "CAPTURE_CALENDAR_BINDING")
    return grade
