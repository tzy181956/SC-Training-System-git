from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
CHECKS = (
    ([sys.executable, "-m", "compileall", "app"], "python -m compileall app"),
    ([sys.executable, "scripts/migrate_db.py", "ensure"], "python scripts/migrate_db.py ensure"),
    ([sys.executable, "-m", "pytest", "-q"], "pytest -q"),
)


def main() -> int:
    for command, label in CHECKS:
        print(f"[BACKEND_CHECK] Running: {label}", flush=True)
        subprocess.run(command, cwd=BACKEND_DIR, check=True)
    print("[BACKEND_CHECK] All checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
