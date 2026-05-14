from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _run(
    command: list[str],
    label: str,
    *,
    cwd: Path = BACKEND_DIR,
    env: dict[str, str] | None = None,
) -> None:
    print(f"[BACKEND_CHECK] Running: {label}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _database_env(db_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    database_url = f"sqlite:///{db_path.as_posix()}"
    env["DATABASE_URL"] = database_url
    env["ALEMBIC_DATABASE_URL"] = database_url
    env.setdefault("APP_ENV", "development")
    env.setdefault("SECRET_KEY", "backend-check-secret-key")
    return env


def _assert_single_alembic_head() -> str:
    config = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    print(f"[BACKEND_CHECK] Alembic heads: {', '.join(heads) or '(none)'}", flush=True)
    if len(heads) != 1:
        raise RuntimeError(f"Expected exactly one Alembic head, got {len(heads)}: {heads}")
    return heads[0]


def _get_base_revision() -> str:
    config = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(config)
    bases = script.get_bases()
    if len(bases) != 1:
        raise RuntimeError(f"Expected exactly one Alembic base revision, got {len(bases)}: {bases}")
    return bases[0]


def _run_alembic_check_or_fallback(env: dict[str, str]) -> None:
    command = [sys.executable, "-m", "alembic", "-c", "alembic.ini", "check"]
    label = "python -m alembic -c alembic.ini check"
    print(f"[BACKEND_CHECK] Running: {label}", flush=True)
    result = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode == 0:
        return

    output = result.stdout or ""
    unsupported_check = (
        "check" in output
        and (
            "invalid choice" in output
            or "No such command" in output
            or "unrecognized arguments" in output
        )
    )
    if unsupported_check:
        print(
            "[BACKEND_CHECK] Alembic check is not supported by this Alembic version; "
            "falling back to migrate_db.py ensure.",
            flush=True,
        )
        _run(
            [sys.executable, "scripts/migrate_db.py", "ensure"],
            "python scripts/migrate_db.py ensure",
            env=env,
        )
        return

    raise subprocess.CalledProcessError(result.returncode, command)


def _run_migration_checks() -> None:
    _run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "heads"],
        "python -m alembic -c alembic.ini heads",
    )
    head_revision = _assert_single_alembic_head()
    base_revision = _get_base_revision()

    with tempfile.TemporaryDirectory(prefix="sc_training_backend_check_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)

        empty_env = _database_env(temp_dir / "empty.db")
        _run(
            [sys.executable, "scripts/migrate_db.py", "ensure"],
            "python scripts/migrate_db.py ensure (temporary empty database)",
            env=empty_env,
        )
        _run_alembic_check_or_fallback(empty_env)

        historical_env = _database_env(temp_dir / "historical.db")
        _run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", base_revision],
            f"python -m alembic -c alembic.ini upgrade {base_revision} (simulated historical database)",
            env=historical_env,
        )
        _run(
            [sys.executable, "scripts/migrate_db.py", "ensure"],
            f"python scripts/migrate_db.py ensure (simulated historical database -> {head_revision})",
            env=historical_env,
        )
        _run_alembic_check_or_fallback(historical_env)


def _has_pytest_tests() -> bool:
    tests_dir = BACKEND_DIR / "tests"
    return tests_dir.exists() and any(tests_dir.rglob("test_*.py"))


def main() -> int:
    _run([sys.executable, "-m", "compileall", "app", "scripts"], "python -m compileall app scripts")
    _run([sys.executable, str(REPO_ROOT / "scripts" / "check_text_encoding.py")], "python scripts/check_text_encoding.py")
    _run_migration_checks()
    if _has_pytest_tests():
        _run([sys.executable, "-m", "pytest", "-q"], "pytest -q")
    else:
        print("[BACKEND_CHECK] No backend pytest tests were found.", flush=True)
    print("[BACKEND_CHECK] All checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except RuntimeError as exc:
        print(f"[BACKEND_CHECK] {exc}", flush=True)
        raise SystemExit(1) from exc
