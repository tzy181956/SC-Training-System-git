from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from app.core.database import SessionLocal
from app.models import User
from app.services import user_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local application user interactively.")
    parser.add_argument("--username", required=True, help="Login username.")
    parser.add_argument("--display-name", required=True, help="Display name shown in the UI.")
    parser.add_argument(
        "--role-code",
        required=True,
        choices=["admin", "coach"],
        help="Role code to create.",
    )
    parser.add_argument("--sport-id", type=int, help="Optional sport id. Required for coach users.")
    parser.add_argument(
        "--allow-sportless-role",
        action="store_true",
        help="Allow creating coach users without sport binding for initial setup or local testing.",
    )
    return parser


def prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        raise SystemExit("Password confirmation mismatch. No user was created.")
    return password


def main() -> None:
    args = build_parser().parse_args()
    password = prompt_password()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == args.username.strip()).first()
        if existing:
            print(f"[USER] Username already exists: {existing.username}")
            raise SystemExit(0)

        user = user_service.create_user(
            db,
            username=args.username,
            display_name=args.display_name,
            role_code=args.role_code,
            password=password,
            sport_id=args.sport_id,
            actor_name="系统脚本",
            allow_sportless_role=args.allow_sportless_role,
        )
    finally:
        db.close()

    if args.role_code == "coach" and args.sport_id is None:
        print("[USER] Warning: coach user created without sport_id. Sport-scoped APIs may reject this account until a sport is assigned.")

    print(f"[USER] Created: {user.username}")
    print(f"[USER] Display name: {user.display_name}")
    print(f"[USER] Role: {user.role_code}")
    print(f"[USER] Sport id: {user.sport_id if user.sport_id is not None else 'none'}")


if __name__ == "__main__":
    main()
