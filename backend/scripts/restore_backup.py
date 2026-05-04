from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from app.core.database import SessionLocal
from app.services import backup_service, dangerous_operation_service
from safety_utils import require_destructive_confirmation


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise SystemExit("Usage: python backend/scripts/restore_backup.py <backup-file>")

    backup_file = Path(sys.argv[1]).expanduser().resolve()
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    db_path = backup_service.get_database_path()
    require_destructive_confirmation(
        action_label="Restore backup and overwrite current live database",
        confirmation_phrase=dangerous_operation_service.RESTORE_BACKUP_CONFIRMATION,
        affected_items=[
            "当前数据库中的训练记录",
            "当前数据库中的模板、动作库和测试数据",
            "当前数据库中的日志与同步状态",
        ],
    )

    pre_restore_backup = backup_service.create_pre_dangerous_operation_backup(label="before_restore_backup")
    if pre_restore_backup.backup_path:
        print(f"[BACKUP] Backup created before restore: {pre_restore_backup.backup_path}")

    backup_service.restore_database_file_from_backup_path(
        source_backup_path=backup_file,
        target_db_path=db_path,
    )

    with SessionLocal() as db:
        dangerous_operation_service.log_dangerous_operation(
            db,
            operation_key="restore_backup",
            object_type="database",
            actor_name="系统脚本",
            source="script",
            confirmation_phrase=dangerous_operation_service.RESTORE_BACKUP_CONFIRMATION,
            summary="恢复数据库备份并覆盖当前线上库",
            impact_scope={
                "restored_from": str(backup_file),
                "database_path": str(db_path),
            },
            backup_path=pre_restore_backup.backup_path,
            extra_data={"restored_from": str(backup_file)},
        )
        db.commit()

    print(f"[RESTORE] Database restored from: {backup_file}")
    print(f"[RESTORE] Active database: {db_path}")


if __name__ == "__main__":
    main()
