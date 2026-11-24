"""Compose the Codex capture contract from live AlmondRhino advertisements."""
from copy import deepcopy
from uuid import UUID


MODE_FIELDS = {
    "capture_01-conditioning_pass": {"rgb_mode": "RGB 패스에 적용. 생략 시 Rendered.",
                                     "edge_mode": "에지 패스에 적용. 생략 시 Technical."},
    "capture_02-inspection": {"display_mode": "이 타일에 적용. 생략 시 원본 뷰 모드."},
    "capture_03-current_view": {"display_mode": "작업 뷰에 적용. 생략 시 현재 모드."},
    "capture_04-defined_view": {"display_mode": "Named View 전용. 생략 시 Shaded."},
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
    if not fields:
        return
    tool.input_schema = deepcopy(tool.input_schema)
    props = tool.input_schema["properties"]
    if tool.name == "capture_02-inspection":
        tile = props["views"]["items"]
        tile["additionalProperties"] = False
        props = tile.setdefault("properties", {})
        props.update(direction={"type": "string"}, label={"type": "string"},
                     object_ids={"type": "array", "items": {"type": "string"}},
                     frame_objects={"type": "boolean"})
    for field, usage in fields.items():
        if modes:
            props[field] = {"type": "string", "enum": list(modes),
                            "description": "세션 시작 시 Rhino 뷰 메뉴에서 확인한 GUID. 실시간 렌더 모드는 캡처에서 제외. "
                                           + usage}
        else:
            props.pop(field, None)


def menu_input_error(name, arguments, modes):
    fields = MODE_FIELDS.get(name)
    if fields:
        entries = arguments.get("views", []) if name == "capture_02-inspection" else [arguments]
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and any(key in entry and entry[key] not in modes for key in fields):
                    return ("The requested display mode GUID is absent from this session's View Display Mode Menu. "
                            "After changing Rhino hosts or menu settings, start a new Codex session.")
