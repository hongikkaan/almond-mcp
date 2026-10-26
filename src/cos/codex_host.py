"""Direct local Codex MCP entry. Does not start or import the CoS app entry."""
from pathlib import Path
from external_host import main as _main, run
from runtime import ROOT


def main(data: Path = ROOT / "data"):
    _main(data, client="codex")


if __name__ == "__main__":
    run("codex")
