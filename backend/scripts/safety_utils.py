from __future__ import annotations


def require_destructive_confirmation(*, action_label: str, confirmation_phrase: str, affected_items: list[str]) -> None:
    print()
    print("[DANGER] This script will perform a destructive data operation.")
    print(f"[DANGER] Action: {action_label}")
    print("[DANGER] The following data will be cleared before continuing:")
    for item in affected_items:
        print(f"  - {item}")
    print("[DANGER] Training templates and exercise library will be kept.")
    print()
    print(f"Type exactly: {confirmation_phrase}")
    user_input = input("> ").strip()
    if user_input != confirmation_phrase:
        raise SystemExit("Confirmation mismatch. No data was changed.")
