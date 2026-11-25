import asyncio
import json
from types import SimpleNamespace
import zlib

from fastmcp import FastMCP

from almond_mcp.features.grasshopper.ghx_parser import GHParser
from almond_mcp.features.grasshopper.library import LibraryIndexer
from almond_mcp.features.grasshopper.tools import register


def test_parser_preserves_component_precedence_and_description_order(tmp_path):
    definition = tmp_path / "logic.GH"
    definition.write_bytes(zlib.compress(b"\0".join((
        b"7PointLoad",
        b"9PointLoad",
        b"pOiNtLoAd",
        b"Gravity Karamba",
        b"Analyze",
        b"Karamba alone is a description",
        b"31A descriptive sentence.",
        b"32A descriptive sentence.",
        b"31A descriptive sentence.",
        b"Gravity is a component match",
    ))))

    parsed = GHParser(str(definition), capsule_dir=str(tmp_path)).parse()

    assert [(item.name, item.category) for item in parsed.components] == [
        ("PointLoad", "kangaroo"),
        ("pOiNtLoAd", "kangaroo"),
        ("Gravity Karamba", "karamba"),
        ("Analyze", "karamba"),
        ("Gravity is a component match", "kangaroo"),
    ]
    assert parsed.all_descriptions == [
        "Karamba alone is a description",
        "A descriptive sentence.",
        "A descriptive sentence.",
    ]


def test_public_logic_prefers_ghx_and_preserves_metadata(tmp_path):
    (tmp_path / "mixed.gh").write_bytes(zlib.compress(b"Gravity"))
    (tmp_path / "mixed.ghx").write_bytes(zlib.compress(b"Analyze"))
    (tmp_path / "mixed.json").write_text(
        '{"nested": [NaN, {"limit": 1e9999}, -Infinity]}', encoding="utf-8"
    )
    (tmp_path / "legacy.json").write_text('{"example": true}', encoding="utf-8")

    server = FastMCP("grasshopper")
    register(server, SimpleNamespace(
        LIBRARY_DIR=str(tmp_path),
        CAPSULE_LIBRARY_DIR=str(tmp_path),
        indexer=LibraryIndexer(str(tmp_path)),
    ))

    async def call(name, arguments):
        result = await server.call_tool(name, arguments)
        return json.loads(result.content[0].text)

    logic = asyncio.run(call("grasshopper_01-get_logic", {
        "logic_id": "MIXED", "field_groups": ["ports"],
    }))
    assert logic["file_name"] == "mixed.ghx"
    assert logic["components"] == [{"name": "Analyze", "category": "karamba", "descriptions": []}]
    assert logic["metadata"] == {"nested": [None, {"limit": None}, None]}

    legacy = asyncio.run(call("grasshopper_01-get_logic", {"logic_id": "legacy"}))
    assert legacy["metadata"] == {"example": True}

    library = asyncio.run(call("grasshopper_03-list_library", {"include_ids": True}))
    assert library["total_entries"] == 2
    assert library["logic_ids"] == library["logic_names"] == ["legacy", "mixed"]
