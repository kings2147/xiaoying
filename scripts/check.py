"""Save a final unit-test report and replay audit without any model calls."""
import io
import json
import platform
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (ROOT / "examples/tests.txt").write_text(stream.getvalue(), encoding="utf-8")
    audit = subprocess.run([sys.executable, str(ROOT / "scripts/audit_evidence.py")], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8")
    report = {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "platform": platform.system(), "unit_tests": {"run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors), "passed": result.wasSuccessful()},
              "evidence_audit": json.loads(audit.stdout) if audit.stdout.strip() else {"passed": False},
              "passed": result.wasSuccessful() and audit.returncode == 0}
    (ROOT / "examples/validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
