from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models import User
from app.schemas.backup_restore import BackupItemRead, BackupListRead, BackupRestorePayload, BackupRestoreRead, RestoreScopeRead
from app.services import backup_service, dangerous_operation_service


router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("", response_model=BackupListRead)
def list_backups(current_user: User = Depends(require_roles("admin"))):
    _ = current_user
    policy = backup_service.describe_backup_policy()
    items = backup_service.list_backup_catalog()
    scopes = backup_service.list_restore_scopes()
    return BackupListRead(
        backup_directory=str(policy["backup_directory"]),
        filename_pattern=str(policy["filename_pattern"]),
        keep_recent_days=int(policy["keep_recent_days"]),
        keep_recent_weeks=int(policy["keep_recent_weeks"]),
        items=[
            BackupItemRead(
                filename=item.filename,
                path=str(item.path),
                stem=item.stem,
                restore_point_at=item.restore_point_at,
                file_modified_at=item.file_modified_at,
                size_bytes=item.size_bytes,
                trigger=item.trigger,
                trigger_label=item.trigger_label,
                label=item.label,
                naming_scheme=item.naming_scheme,
                is_managed=item.is_managed,
            )
            for item in items
        ],
        available_restore_scopes=[
            RestoreScopeRead(
                key=scope.key,
                label=scope.label,
                description=scope.description,
                impact_summary=scope.impact_summary,
                affected_tables=scope.tables,
            )
            for scope in scopes
        ],
    )


@router.post("/restore", response_model=BackupRestoreRead)
def restore_backup(
    payload: BackupRestorePayload,
    current_user: User = Depends(require_roles("admin")),
):
    dangerous_operation_service.require_confirmation(
        payload,
        action_label="恢复备份",
        confirmation_phrase=dangerous_operation_service.RESTORE_BACKUP_CONFIRMATION,
    )
    result = backup_service.restore_backup(
        backup_filename=payload.backup_filename,
        restore_scope_key=payload.restore_scope,
        team_id=payload.team_id,
        actor_name=payload.actor_name or current_user.display_name,
    )
    message = f"已按备份时间点 {result.backup_record.restore_point_at.strftime('%Y-%m-%d %H:%M:%S')} 恢复{result.scope.label}"
    if result.post_restore_note:
        message = f"{message}；{result.post_restore_note}"
    return BackupRestoreRead(
        backup_filename=result.backup_record.filename,
        backup_path=str(result.backup_record.path),
        restore_scope=result.scope.key,
        restore_scope_label=result.scope.label,
        restore_point_at=result.backup_record.restore_point_at,
        team_id=result.team_id,
        team_name=result.team_name,
        restored_tables=result.restored_tables,
        restored_row_counts=result.restored_row_counts,
        pre_restore_backup_path=(
            str(result.pre_restore_backup.backup_path)
            if result.pre_restore_backup.backup_path
            else None
        ),
        message=message,
    )
