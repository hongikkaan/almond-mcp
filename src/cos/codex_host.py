"""Start beyond from the address used by existing Codex registrations."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "beyond"))
from external_host import main, run


if __name__ == "__main__":
    run()
