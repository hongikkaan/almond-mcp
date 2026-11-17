"""Validate the shared metadata/content boundary of a distributed archive."""


def verify_catalogue(catalogue: dict) -> list[dict]:
    records = catalogue["assets"]
    counts = catalogue["counts"]
    generated = [record for record in records if record.get("source_library") == "generated"]
    community = [record for record in records if record.get("source_library") == "drawing"]
    if (len(records) != 57 or len(generated) != 50 or len(community) != 7
            or len({record["id"] for record in records}) != len(records)):
        raise ValueError("Expected 50 generated models and 7 unique community metadata records.")
    expected = {
        "assets": len(records),
        "models": sum(record["kind"] == "model" for record in records),
        "elements": sum(record["kind"] == "element" for record in records),
        "drawing_packages": 10,
        "views": 60,
    }
    if counts != expected or counts["models"] + counts["elements"] != counts["assets"]:
        raise ValueError(f"Unexpected catalogue: {counts}")
    if any(record["kind"] != "model" or not record["source_available"] or not record["source_file"]
           for record in generated):
        raise ValueError("Generated catalogue model sources must be available from the distribution.")
    if any(record["available"] or record["source_available"]
           or any(record.get(key) for key in ("model", "preview", "source_file", "drawing", "contract"))
           for record in community):
        raise ValueError("Community records must contain metadata only.")
    return generated
