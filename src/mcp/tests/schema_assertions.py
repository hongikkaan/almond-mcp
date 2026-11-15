"""Check real response fields are declared, beyond permissive JSON validation."""
from jsonschema import Draft202012Validator


def assert_described_payload(value, schema):
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)

    def visit(item, contract, path):
        if isinstance(item, dict):
            if "type" not in contract:  # Explicitly untyped external values.
                return
            properties = contract.get("properties", {})
            additional = contract.get("additionalProperties")
            for name, child in item.items():
                location = f"{path}.{name}"
                if name in properties:
                    assert properties[name].get("description"), location
                    visit(child, properties[name], location)
                elif isinstance(additional, dict):
                    visit(child, additional, location)
                else:
                    assert additional is True, f"Undeclared output field: {location}"
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, contract["items"], f"{path}[{index}]")

    visit(value, schema, "response")
