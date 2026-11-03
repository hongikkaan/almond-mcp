"""Typed list edits and mutation outcomes; no storage or server side effects."""
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StringListPatch(BaseModel):
    """Add/remove string values; omission and empty arrays leave that operation empty."""

    model_config = ConfigDict(extra="forbid", strict=True)
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


@dataclass
class PlanningUpdate:
    record: dict[str, Any]
    changed: bool
    issues: list[dict[str, Any]]


def apply_list_patch(current: list[str], patch: StringListPatch, field: str,
                     *, kind: str | None = None) -> tuple[list[str], list[dict]]:
    """Keep valid edits and report each skipped input without changing current data."""
    values = {operation: [value.strip() for value in getattr(patch, operation)]
              for operation in ("add", "remove")}
    conflicts = set(values["add"]) & set(values["remove"])
    result, issues = list(current), []
    present = {value.strip() for value in current}
    for operation in ("remove", "add"):
        seen = set()
        for index, value in enumerate(values[operation]):
            reason = None
            if not value:
                reason = "invalid_value"
            elif kind and (not value.startswith(kind + "_") or not value[len(kind) + 1:].strip()):
                reason = "invalid_reference_kind"
            elif value in conflicts:
                reason = "conflicting_operation"
            elif value in seen:
                reason = "duplicate_input"
            elif operation == "add" and value in present:
                reason = "already_present"
            elif operation == "remove" and value not in present:
                reason = "not_found"
            seen.add(value)
            if reason:
                issues.append({"field": field, "operation": operation, "index": index,
                               "value": getattr(patch, operation)[index], "reason": reason})
            elif operation == "remove":
                result = [item for item in result if item.strip() != value]
                present.remove(value)
            else:
                result.append(value)
                present.add(value)
    return result, issues
