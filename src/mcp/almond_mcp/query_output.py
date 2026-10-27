"""Public response projection; stored identities and snapshots stay intact."""

from functools import wraps
from inspect import signature
import json
from typing import Any
from uuid import UUID
from almond_mcp.managed_paths import relative_output
from almond_mcp.tool_response import error_payload


class InvalidFieldGroups(ValueError):
    """An invalid display selection; no feature work has started."""


# Safety and completion evidence is independent of display preferences.
EVIDENCE_FIELDS = frozenset({
    "status", "error", "error_code", "message", "warnings", "warning", "mutation_applied",
    "mutation_state", "registration_applied", "changed", "live_verified", "complete",
    "truncated", "scene_revisions", "proof", "native_proof", "completion",
    "request_id", "operation_id", "conflict", "expected_revision", "actual_revision",
    "errors", "problems", "unverified", "uncertainty", "unsupported", "unsupported_objects",
    "unknown_pairs", "limitations", "coverage", "passed_scope",
    "truncation_reason",
})


def _unconfirmed(record: dict) -> bool:
    return (record.get("status") in ("error", "unknown", "uncertain") or bool(record.get("error"))
            or record.get("mutation_state") in ("unknown", "pending", "uncertain")
            or record.get("complete") is False
            or record.get("requires_reconciliation") is True
            or ("mutation_applied" in record and record["mutation_applied"] is None))


def _evidence_field(key: str) -> bool:
    return (key in EVIDENCE_FIELDS or key.startswith(("requires_", "native_"))
            or key.endswith(("_proof", "_completion")))


def _guid_path(key: str, value) -> bool:
    if key != "path" or not isinstance(value, list) or not value:
        return False
    try:
        for part in value:
            UUID(part)
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def validate_field_groups(field_groups: list[str] | None, group_keys: dict) -> None:
    """Validate the explicit feature contract before store/native work begins."""
    if field_groups is None:
        return
    if not isinstance(field_groups, list) or any(type(group) is not str for group in field_groups):
        raise InvalidFieldGroups("field_groups must be an array of strings.")
    unknown = set(field_groups) - set(group_keys) - {"all"}
    if unknown:
        raise InvalidFieldGroups("Unknown field_groups: " + ", ".join(sorted(unknown)) +
                         ". Supported: " + ", ".join([*group_keys, "all"]))


def select_fields(record: dict, field_groups: list[str] | None, core_keys, group_keys: dict) -> dict:
    """Select a feature's declared fields without changing stored records or evidence."""
    if _unconfirmed(record):
        return record
    if "all" in (field_groups or []):
        return dict(record)
    selected = set(core_keys)
    for group in field_groups or []:
        selected.update(group_keys[group])
    return {key: value for key, value in record.items()
            if key in selected or _evidence_field(key)}


def select_records(records, field_groups: list[str] | None, core_keys, group_keys: dict):
    """Apply the same declared record selection to a single record or a page."""
    if isinstance(records, list):
        return [select_fields(record, field_groups, core_keys, group_keys) for record in records]
    return select_fields(records, field_groups, core_keys, group_keys)


def compact_ack(record: dict, core_keys) -> dict:
    """Keep write handles, revisions and evidence without echoing whole snapshots."""
    if _unconfirmed(record):
        return record
    selected = select_fields(record, None, core_keys, {})
    return {key: value for key, value in selected.items()
            if not key.endswith("_id") or value not in (None, "")}


def project_query(value: Any, *, include_ids: bool = False, supplied: dict | None = None,
                  include_audit: bool = True) -> Any:
    if isinstance(value, list):
        return [project_query(item, include_ids=include_ids, supplied=supplied, include_audit=include_audit) for item in value]
    if not isinstance(value, dict):
        return value
    if _unconfirmed(value):
        return value
    result = {}
    for key, item in value.items():
        if _evidence_field(key):
            result[key] = item
            continue
        if not include_audit and key in {"created_at", "updated_at", "observed_at", "generated_at"}:
            continue
        identity = (key in {"id", "ids", "guid", "guids", "depends_on"}
                    or key.endswith(("_id", "_ids", "_guid", "_guids")) or _guid_path(key, item))
        echoed = supplied and key in supplied and supplied[key] not in (None, "", []) and item == supplied[key]
        if identity and (not include_ids or echoed):
            if isinstance(item, list):
                count_key = key.removesuffix("_ids").removesuffix("_guids") + "_count"
                result.setdefault(count_key, len(item))
            continue
        result[key] = project_query(item, include_ids=include_ids, supplied=supplied, include_audit=include_audit)
    return result


def query_output(function):
    """Wrap JSON query output; callers still declare include_ids in their schema."""
    parameters = signature(function)

    @wraps(function)
    def invoke(*args, **kwargs):
        arguments = parameters.bind(*args, **kwargs)
        arguments.apply_defaults()
        include_ids = arguments.arguments.get("include_ids", False)
        if type(include_ids) is not bool:
            raise ValueError("include_ids must be a boolean.")
        try:
            result = function(*args, **kwargs)
        except InvalidFieldGroups as exc:
            value = error_payload(str(exc), error_code="invalid_arguments")
            return json.dumps(value) if parameters.return_annotation in (str, "str") else value
        is_text = isinstance(result, str)
        value = json.loads(result) if is_text else result
        if isinstance(value, dict) and _unconfirmed(value):
            return result
        groups = arguments.arguments.get("field_groups") or []
        include_audit = "field_groups" not in parameters.parameters or bool({"audit", "all"} & set(groups))
        value = relative_output(project_query(value, include_ids=include_ids, supplied=arguments.arguments,
                                              include_audit=include_audit))
        return json.dumps(value, ensure_ascii=False) if is_text else value

    return invoke
