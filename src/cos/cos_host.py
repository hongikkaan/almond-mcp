"""CoS application entry; keep the already registered command path stable."""
from pathlib import Path
from external_host import main as _main, run
from runtime import ROOT


def main(data: Path = ROOT / "data"):
    _main(data, client="cos")


if __name__ == "__main__":
    run("cos")
