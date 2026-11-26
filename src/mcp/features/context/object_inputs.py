"""Public object-query shapes shared by the executable and inert tool registrations."""
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, SkipValidation, TypeAdapter, with_config
from typing_extensions import TypedDict


NonemptyName = Annotated[str, Field(min_length=1)]
Names = Annotated[list[NonemptyName], Field(min_length=1, max_length=64)]


@with_config(ConfigDict(extra="forbid", strict=True, json_schema_extra={"minProperties": 1}))
class NamedCondition(TypedDict, total=False):
    include: Names
    exclude: Names


@with_config(ConfigDict(extra="forbid", strict=True))
class TextCondition(TypedDict):
    key: NonemptyName
    any_of: Annotated[list[str], Field(min_length=1, max_length=64)]


@with_config(ConfigDict(extra="forbid", strict=True))
class DictionaryCondition(TypedDict):
    source: Literal["attributes", "geometry"]
    key: NonemptyName
    any_of: Annotated[list[str | bool | int | float], Field(min_length=1, max_length=64)]


@with_config(ConfigDict(extra="forbid", strict=True, json_schema_extra={
    "minProperties": 1,
    "allOf": [
        {"if": {"required": [side], "properties": {side: {"minItems": 2}}},
         "then": {"required": [side + "_mode"]},
         "else": {"not": {"required": [side + "_mode"]}}}
        for side in ("include", "exclude")
    ],
}))
class GroupCondition(TypedDict, total=False):
    include: Names
    exclude: Names
    include_mode: Literal["any", "all"]
    exclude_mode: Literal["any", "all"]


@with_config(ConfigDict(extra="forbid", strict=True, json_schema_extra={"minProperties": 1}))
class TextSides(TypedDict, total=False):
    include: Annotated[list[TextCondition], Field(min_length=1, max_length=1)]
    exclude: Annotated[list[TextCondition], Field(min_length=1, max_length=1)]


@with_config(ConfigDict(extra="forbid", strict=True, json_schema_extra={"minProperties": 1}))
class DictionarySides(TypedDict, total=False):
    include: Annotated[list[DictionaryCondition], Field(min_length=1, max_length=1)]
    exclude: Annotated[list[DictionaryCondition], Field(min_length=1, max_length=1)]


DictionaryFilter = Annotated[list[DictionaryCondition], Field(max_length=16)] | DictionarySides


@with_config(ConfigDict(extra="forbid", strict=True))
class FilterFields(TypedDict, total=False):
    layer: NamedCondition
    name: NamedCondition
    object_type: NamedCondition
    block: NamedCondition
    group: GroupCondition
    material: NamedCondition
    name_contains: Annotated[str, Field(max_length=256)]
    user_text: Annotated[list[TextCondition], Field(max_length=16)] | TextSides
    user_dictionary: DictionaryFilter


# Validate inside the handler so invalid calls retain the public JSON error envelope.
ObjectFilters = SkipValidation[FilterFields]
ObjectScope = SkipValidation[Literal["current", "document", "inside_viewport"]]
ObjectResultMode = SkipValidation[Literal["objects", "hierarchy", "summary"]]
FILTERS = TypeAdapter(FilterFields)
