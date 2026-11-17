"""Map the Python release version to the bridge's SemVer spelling."""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src/mcp"))
from almond_mcp import __version__


def bridge_version() -> str:
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:(a|b|rc)(\d+))?", __version__)
    if match is None:
        raise ValueError("Expected a stable, alpha, beta, or rc release version.")
    base, stage, number = match.groups()
    if stage is None:
        return base
    label = {"a": "alpha", "b": "beta", "rc": "rc"}[stage]
    return f"{base}-{label}.{number}"


def write_yak_manifest(destination: Path) -> None:
    template = (ROOT / "src/rhp/RhinoAlmondBridge/yak/manifest.yml").read_bytes()
    if template.count(b"@VERSION@") != 1:
        raise ValueError("Expected exactly one Yak version placeholder.")
    destination.write_bytes(template.replace(b"@VERSION@", bridge_version().encode("ascii")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yak-manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.yak_manifest:
        write_yak_manifest(arguments.yak_manifest)
    else:
        print(bridge_version())
