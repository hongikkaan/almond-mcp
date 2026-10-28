"""Run only disposable fixtures and save a small reproducible verification record."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import unittest

REPO = Path(__file__).resolve().parents[3]
EXTERNAL = REPO / "src" / "cos"
ENGINE = REPO / "src" / "mcp" / "runtime"
TESTS = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / "src" / "mcp"))
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(EXTERNAL))
sys.path.insert(0, str(TESTS))
test_data = EXTERNAL / "data"
test_data.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
suite = unittest.defaultTestLoader.discover(str(TESTS), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
if "almond_mcp.server" in sys.modules:
    raise RuntimeError("Tests must not import the real Almond server.")
report = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
    "seconds": round(time.monotonic() - started, 3),
    "scope": "Disposable Python/C# transport and lifecycle fixtures, extracted helpers, Windows message pipes and directory notifications, broker cleanup, and isolated stdio. No live Rhino geometry or model/DB verification.",
    "live_rhino_integration_tested": False, "original_almond_server_imported": False,
}
(test_data / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
raise SystemExit(0 if result.wasSuccessful() else 1)
