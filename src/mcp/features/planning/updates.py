"""Typed list edits and mutation outcomes; no storage or server side effects."""
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StringListPatch(BaseModel):
    """문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다."""

    model_config = ConfigDict(extra="forbid", strict=True)
    add: list[str] = Field(default_factory=list, description="추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.")
    remove: list[str] = Field(default_factory=list, description="제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.")


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
