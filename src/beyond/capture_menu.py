"""Compose the Codex capture contract from live AlmondRhino advertisements."""
from copy import deepcopy
from uuid import UUID


MODE_FIELDS = {
    "capture_01-conditioning_pass": ("rgb_mode", "edge_mode"),
    "capture_02-inspection": ("display_mode",),
    "capture_03-current_view": ("display_mode",),
    "capture_04-defined_view": ("display_mode",),
}


def common_mode_ids(hosts):
    """Before connection, only offer GUIDs present in every live host."""
    menus = []
    for host in hosts:
        ids = host.get("display_mode_ids")
        if not isinstance(ids, list):
            return ()
        try:
            menu = {str(UUID(value)) for value in ids if isinstance(value, str)}
        except ValueError:
            return ()
        if len(menu) != len(ids) or str(UUID(int=0)) in menu:
            return ()
        menus.append(menu)
    return tuple(sorted(set.intersection(*menus))) if menus else ()


def apply_menu_schema(tool, modes):
    fields = MODE_FIELDS.get(tool.name)
    if not fields or not modes:
        return
    tool.input_schema = deepcopy(tool.input_schema)
    props = tool.input_schema["properties"]
    if tool.name == "capture_02-inspection":
        props = props["views"]["items"]["properties"]
    # Newly opened hosts can accept other modes. The selected Rhino validates each call.
    for field in fields:
        props[field]["examples"] = list(modes)
