"""Public query projection. Stored identities and mutation results stay intact."""

from functools import wraps
from inspect import signature
import json
from typing import Any
from almond_mcp.managed_paths import relative_output


def project_query(value: Any, *, include_ids: bool = False, supplied: dict | None = None) -> Any:
    if isinstance(value, list):
        return [project_query(item, include_ids=include_ids, supplied=supplied) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        identity = key in {"id", "ids", "guid", "guids", "depends_on"} or key.endswith(("_id", "_ids", "_guid", "_guids"))
        echoed = supplied and key in supplied and supplied[key] not in (None, "", []) and item == supplied[key]
        if identity and (not include_ids or echoed):
            if isinstance(item, list):
                count_key = key.removesuffix("_ids").removesuffix("_guids") + "_count"
                result.setdefault(count_key, len(item))
            continue
        result[key] = project_query(item, include_ids=include_ids, supplied=supplied)
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
        result = function(*args, **kwargs)
        is_text = isinstance(result, str)
        value = json.loads(result) if is_text else result
        if isinstance(value, dict) and value.get("status") == "error":
            return result
        value = relative_output(project_query(value, include_ids=include_ids, supplied=arguments.arguments))
        return json.dumps(value, ensure_ascii=False) if is_text else value

    return invoke
