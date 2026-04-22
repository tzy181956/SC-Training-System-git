from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".vue",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".css",
    ".html",
    ".bat",
    ".cmd",
    ".ps1",
    ".ini",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
}
SKIP_FILES = {
    Path("scripts/check_text_encoding.py"),
}
MOJIBAKE_PATTERNS = [
    "浣撹",
    "璁",
    "鍔ㄤ綔",
    "妯℃澘",
    "鍒嗛厤",
    "杩愬姩鍛",
    "涓€閿",
    "鍚姩",
    "鏁版嵁",
    "鐪熷疄",
    "浣撹剛鐜",
    "鍙嶅悜璺",
    "闈欒共璺",
]
PRIVATE_USE_RE = re.compile(r"[\uE000-\uF8FF]")


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.relative_to(root) in SKIP_FILES:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def inspect_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"UTF-8 decode failed: {exc}"]

    if "\ufffd" in text:
        issues.append("contains replacement character U+FFFD")
    if PRIVATE_USE_RE.search(text):
        issues.append("contains Private Use Area character")
    for token in MOJIBAKE_PATTERNS:
        if token in text:
            issues.append(f"contains suspicious mojibake token: {token}")
    return issues


def main() -> int:
    suspicious: list[tuple[Path, list[str]]] = []
    for path in iter_text_files(ROOT):
        issues = inspect_file(path)
        if issues:
            suspicious.append((path, issues))

    if not suspicious:
        print("No obvious text-encoding problems found.")
        return 0

    print("Suspicious text-encoding issues found:")
    for path, issues in suspicious:
        rel = path.relative_to(ROOT)
        print(f"- {rel}")
        for issue in issues:
            print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
