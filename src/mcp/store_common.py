"""Shared serialization and reconciliation errors for feature-owned stores."""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

import json
from datetime import datetime, timezone
from typing import Any

RETIRED_LIBRARY_ID = "retired"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

def _decode(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)

class ComponentReconciliationError(RuntimeError):
    """Rhino may have changed although the ledger transaction did not finish."""

    def __init__(self, component_id: str, model_path: str, message: str):
        super().__init__(
            read_instruction(__file__, 'response-58').format(message, component_id)
        )
        self.component_id = component_id
        self.model_path = model_path
        self.requires_reconciliation = True

class DrawingSheetReconciliationError(RuntimeError):
    """A Layout operation may have succeeded while its ledger transaction failed."""

    def __init__(self, sheet_id: str, model_path: str, message: str):
        super().__init__(read_instruction(__file__, 'response-59').format(message, sheet_id))
        self.sheet_id = sheet_id
        self.model_path = model_path

class _NativeRejected(ValueError):
    """A native response explicitly certifies no change or a verified rollback."""
