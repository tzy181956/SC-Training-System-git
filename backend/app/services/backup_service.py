from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.exceptions import bad_request, not_found


BACKUP_KEEP_DAYS = 7
BACKUP_KEEP_WEEKS = 8
MANAGED_BACKUP_PATTERN = re.compile(
    r"^(?P<stem>.+)-(?P<timestamp>\d{8}-\d{6})-(?P<trigger>[a-z0-9_]+)(?:-(?P<label>[a-z0-9_]+))?\.db$"
)
LEGACY_MIGRATION_BACKUP_PATTERN = re.compile(
    r"^(?P<stem>.+)\.migration-backup-(?P<timestamp>\d{8}-\d{6})\.db$"
)
TRIGGER_LABELS = {
    "daily_auto": "每日自动备份",
    "before_migration": "迁移前备份",
    "before_dangerous": "危险操作前备份",
    "legacy_migration": "旧版迁移备份",
    "manual": "手动备份",
}
_RESTORE_LOCK = threading.Lock()


@dataclass(slots=True)
class BackupRecord:
    path: Path
    stem: str
    timestamp: datetime
    trigger: str
    label: str | None


@dataclass(slots=True)
class BackupResult:
    created: bool
    backup_path: Path | None
    trigger: str
    label: str | None
    skipped_reason: str | None = None
    deleted_paths: list[Path] | None = None


@dataclass(slots=True)
class BackupCatalogRecord:
    path: Path
    filename: str
    stem: str
    restore_point_at: datetime
    file_modified_at: datetime
    size_bytes: int
    trigger: str | None
    trigger_label: str | None
    label: str | None
    naming_scheme: str
    is_managed: bool


@dataclass(slots=True)
class RestoreScopeDefinition:
    key: str
    label: str
    description: str
    tables: list[str] = field(default_factory=list)
    impact_summary: list[str] = field(default_factory=list)
    object_type: str = "database"


@dataclass(slots=True)
class RestoreResult:
    backup_record: BackupCatalogRecord
    scope: RestoreScopeDefinition
    restored_tables: list[str]
    pre_restore_backup: BackupResult


RESTORE_SCOPE_DEFINITIONS: dict[str, RestoreScopeDefinition] = {
    "full_database": RestoreScopeDefinition(
        key="full_database",
        label="整库恢复",
        description="用所选备份整体覆盖当前正式数据库。",
        tables=[],
        impact_summary=[
            "会整体覆盖当前训练、模板、动作库、测试和日志数据。",
            "恢复前系统会先自动为当前线上库再做一份兜底备份。",
            "建议在无人录课时执行，避免覆盖正在录入的新数据。",
        ],
        object_type="database",
    ),
    "training_records": RestoreScopeDefinition(
        key="training_records",
        label="训练数据恢复",
        description="只恢复训练课执行、组记录、同步异常与课后修改日志。",
        tables=[
            "training_sessions",
            "training_session_items",
            "set_records",
            "training_session_edit_logs",
            "training_sync_conflicts",
            "training_sync_issues",
        ],
        impact_summary=[
            "只覆盖训练执行相关数据，不改模板、动作库和测试数据。",
            "恢复前会先自动备份当前正式数据库。",
            "如果当前库缺少备份内引用的运动员、计划或动作，将拒绝部分恢复并建议改用整库恢复。",
        ],
        object_type="training_records",
    ),
    "test_records": RestoreScopeDefinition(
        key="test_records",
        label="测试数据恢复",
        description="只恢复测试记录，不改训练课、模板和动作库。",
        tables=["test_records"],
        impact_summary=[
            "只覆盖测试记录表，不影响训练执行数据。",
            "恢复前会先自动备份当前正式数据库。",
            "如果当前库缺少备份内引用的运动员，将拒绝部分恢复并提示先补回基础数据或整库恢复。",
        ],
        object_type="test_records",
    ),
}


def create_pre_migration_backup(*, label: str, now: datetime | None = None) -> BackupResult:
    return create_backup(trigger="before_migration", label=label, now=now)


def create_pre_dangerous_operation_backup(*, label: str, now: datetime | None = None) -> BackupResult:
    return create_backup(trigger="before_dangerous", label=label, now=now)


def ensure_daily_backup(*, now: datetime | None = None) -> BackupResult:
    resolved_now = _resolve_now(now)
    backup_dir = get_backup_directory()
    for record in list_managed_backups(backup_dir=backup_dir):
        if record.trigger == "daily_auto" and record.timestamp.date() == resolved_now.date():
            return BackupResult(
                created=False,
                backup_path=record.path,
                trigger="daily_auto",
                label=record.label,
                skipped_reason="daily backup already exists",
                deleted_paths=[],
            )
    return create_backup(trigger="daily_auto", label="scheduled", now=resolved_now)


def create_backup(
    *,
    trigger: str,
    label: str | None = None,
    now: datetime | None = None,
    backup_dir: Path | None = None,
    source_db_path: Path | None = None,
) -> BackupResult:
    resolved_now = _resolve_now(now)
    resolved_label = _slugify(label)
    resolved_trigger = _slugify(trigger)
    db_path = source_db_path or get_database_path()
    if not db_path.exists():
        raise RuntimeError(f"Database file not found: {db_path}")

    target_dir = backup_dir or get_backup_directory()
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp_text = resolved_now.strftime("%Y%m%d-%H%M%S")
    filename = f"{db_path.stem}-{timestamp_text}-{resolved_trigger}"
    if resolved_label:
        filename = f"{filename}-{resolved_label}"
    filename = f"{filename}{db_path.suffix}"

    backup_path = target_dir / filename
    temp_path = backup_path.with_suffix(f"{backup_path.suffix}.tmp")
    _copy_sqlite_database(source_db_path=db_path, target_path=temp_path)
    temp_path.replace(backup_path)

    deleted_paths = apply_retention_policy(backup_dir=target_dir, now=resolved_now)
    return BackupResult(
        created=True,
        backup_path=backup_path,
        trigger=resolved_trigger,
        label=resolved_label,
        skipped_reason=None,
        deleted_paths=deleted_paths,
    )


def apply_retention_policy(*, backup_dir: Path | None = None, now: datetime | None = None) -> list[Path]:
    target_dir = backup_dir or get_backup_directory()
    resolved_now = _resolve_now(now)
    records = list_managed_backups(backup_dir=target_dir)
    if not records:
        return []

    sorted_records = sorted(records, key=lambda item: item.timestamp, reverse=True)
    keep_paths: set[Path] = set()
    daily_cutoff_date = (resolved_now - timedelta(days=BACKUP_KEEP_DAYS - 1)).date()
    weekly_cutoff_date = (resolved_now - timedelta(weeks=BACKUP_KEEP_WEEKS)).date()
    kept_weeks: set[tuple[int, int]] = set()

    latest_record = sorted_records[0]
    keep_paths.add(latest_record.path)

    for record in sorted_records:
        record_date = record.timestamp.date()
        if record_date >= daily_cutoff_date:
            keep_paths.add(record.path)
            continue
        if record_date >= weekly_cutoff_date:
            iso_year, iso_week, _ = record.timestamp.isocalendar()
            week_key = (iso_year, iso_week)
            if week_key not in kept_weeks:
                kept_weeks.add(week_key)
                keep_paths.add(record.path)

    deleted_paths: list[Path] = []
    for record in sorted_records:
        if record.path in keep_paths:
            continue
        try:
            record.path.unlink()
            deleted_paths.append(record.path)
        except FileNotFoundError:
            continue

    return deleted_paths


def list_managed_backups(*, backup_dir: Path | None = None) -> list[BackupRecord]:
    target_dir = backup_dir or get_backup_directory()
    if not target_dir.exists():
        return []

    records: list[BackupRecord] = []
    for path in target_dir.glob("*.db"):
        match = MANAGED_BACKUP_PATTERN.match(path.name)
        if not match:
            continue
        timestamp = datetime.strptime(match.group("timestamp"), "%Y%m%d-%H%M%S")
        records.append(
            BackupRecord(
                path=path,
                stem=match.group("stem"),
                timestamp=timestamp,
                trigger=match.group("trigger"),
                label=match.group("label"),
            )
        )
    return records


def list_backup_catalog(*, backup_dir: Path | None = None) -> list[BackupCatalogRecord]:
    target_dir = backup_dir or get_backup_directory()
    if not target_dir.exists():
        return []

    records: list[BackupCatalogRecord] = []
    for path in target_dir.glob("*.db"):
        records.append(_build_backup_catalog_record(path))

    records.sort(key=lambda item: (item.restore_point_at, item.file_modified_at, item.filename), reverse=True)
    return records


def get_backup_catalog_record(backup_filename: str, *, backup_dir: Path | None = None) -> BackupCatalogRecord:
    safe_name = Path(backup_filename).name
    if safe_name != backup_filename:
        raise bad_request("备份文件名不合法")

    target_dir = backup_dir or get_backup_directory()
    backup_path = (target_dir / safe_name).resolve()
    if not backup_path.exists() or not backup_path.is_file():
        raise not_found("备份文件不存在")
    if backup_path.parent != target_dir.resolve():
        raise bad_request("备份文件路径不合法")
    return _build_backup_catalog_record(backup_path)


def list_restore_scopes() -> list[RestoreScopeDefinition]:
    return list(RESTORE_SCOPE_DEFINITIONS.values())


def get_restore_scope(scope_key: str) -> RestoreScopeDefinition:
    scope = RESTORE_SCOPE_DEFINITIONS.get(scope_key)
    if scope is None:
        raise bad_request("不支持的恢复范围")
    return scope


def restore_backup(
    *,
    backup_filename: str,
    restore_scope_key: str,
    actor_name: str | None = None,
) -> RestoreResult:
    backup_record = get_backup_catalog_record(backup_filename)
    restore_scope = get_restore_scope(restore_scope_key)

    with _RESTORE_LOCK:
        pre_restore_backup = create_pre_dangerous_operation_backup(
            label=f"before_restore_{restore_scope.key}"
        )
        database_path = get_database_path()

        if restore_scope.key == "full_database":
            restore_database_file_from_backup_path(
                source_backup_path=backup_record.path,
                target_db_path=database_path,
            )
            restored_tables = ["*"]
        else:
            restored_tables = restore_partial_scope_from_backup_path(
                source_backup_path=backup_record.path,
                target_db_path=database_path,
                restore_scope=restore_scope,
            )

        from app.core.schema_sync import ensure_runtime_schema

        ensure_runtime_schema()
        _log_restore_operation(
            backup_record=backup_record,
            restore_scope=restore_scope,
            pre_restore_backup=pre_restore_backup,
            restored_tables=restored_tables,
            actor_name=actor_name,
        )

    return RestoreResult(
        backup_record=backup_record,
        scope=restore_scope,
        restored_tables=restored_tables,
        pre_restore_backup=pre_restore_backup,
    )


def get_backup_directory() -> Path:
    return get_database_path().parent / "backups"


def get_database_path() -> Path:
    database_url = get_settings().database_url
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError(f"Only sqlite database URLs are supported: {database_url}")
    return Path(database_url.removeprefix(prefix))


def describe_backup_policy() -> dict[str, str | int | Path]:
    return {
        "backup_directory": str(get_backup_directory()),
        "filename_pattern": "training-YYYYMMDD-HHMMSS-trigger-label.db",
        "keep_recent_days": BACKUP_KEEP_DAYS,
        "keep_recent_weeks": BACKUP_KEEP_WEEKS,
    }


def restore_database_file_from_backup_path(*, source_backup_path: Path, target_db_path: Path) -> None:
    if not source_backup_path.exists():
        raise not_found("备份文件不存在")

    temp_path = target_db_path.with_suffix(f"{target_db_path.suffix}.restore_tmp")
    if temp_path.exists():
        temp_path.unlink()

    engine.dispose()
    _copy_sqlite_database(source_db_path=source_backup_path, target_path=temp_path)
    temp_path.replace(target_db_path)


def restore_partial_scope_from_backup_path(
    *,
    source_backup_path: Path,
    target_db_path: Path,
    restore_scope: RestoreScopeDefinition,
) -> list[str]:
    if restore_scope.key == "full_database":
        raise bad_request("整库恢复不应走部分恢复路径")

    engine.dispose()
    connection = sqlite3.connect(target_db_path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("ATTACH DATABASE ? AS restore_source", (str(source_backup_path),))
        restored_tables: list[str] = []
        try:
            connection.execute("BEGIN IMMEDIATE")
            _validate_restore_dependencies(connection, restore_scope)
            for table_name in restore_scope.tables:
                restored = _replace_table_data_from_backup(connection, table_name)
                if restored:
                    restored_tables.append(table_name)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.execute("DETACH DATABASE restore_source")
            connection.execute("PRAGMA foreign_keys = ON")
        return restored_tables
    finally:
        connection.close()


def _copy_sqlite_database(*, source_db_path: Path, target_path: Path) -> None:
    source_connection = sqlite3.connect(source_db_path)
    try:
        target_connection = sqlite3.connect(target_path)
        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
    finally:
        source_connection.close()


def _resolve_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now().astimezone()
    if now.tzinfo is None:
        return now.astimezone()
    return now.astimezone()


def _slugify(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or None


def _build_backup_catalog_record(path: Path) -> BackupCatalogRecord:
    file_modified_at = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    size_bytes = path.stat().st_size

    managed_match = MANAGED_BACKUP_PATTERN.match(path.name)
    if managed_match:
        timestamp = datetime.strptime(managed_match.group("timestamp"), "%Y%m%d-%H%M%S").astimezone()
        trigger = managed_match.group("trigger")
        return BackupCatalogRecord(
            path=path,
            filename=path.name,
            stem=managed_match.group("stem"),
            restore_point_at=timestamp,
            file_modified_at=file_modified_at,
            size_bytes=size_bytes,
            trigger=trigger,
            trigger_label=TRIGGER_LABELS.get(trigger, trigger),
            label=managed_match.group("label"),
            naming_scheme="managed",
            is_managed=True,
        )

    legacy_match = LEGACY_MIGRATION_BACKUP_PATTERN.match(path.name)
    if legacy_match:
        timestamp = datetime.strptime(legacy_match.group("timestamp"), "%Y%m%d-%H%M%S").astimezone()
        trigger = "legacy_migration"
        return BackupCatalogRecord(
            path=path,
            filename=path.name,
            stem=legacy_match.group("stem"),
            restore_point_at=timestamp,
            file_modified_at=file_modified_at,
            size_bytes=size_bytes,
            trigger=trigger,
            trigger_label=TRIGGER_LABELS.get(trigger, trigger),
            label=None,
            naming_scheme="legacy_migration",
            is_managed=False,
        )

    return BackupCatalogRecord(
        path=path,
        filename=path.name,
        stem=path.stem,
        restore_point_at=file_modified_at,
        file_modified_at=file_modified_at,
        size_bytes=size_bytes,
        trigger=None,
        trigger_label=None,
        label=None,
        naming_scheme="unknown",
        is_managed=False,
    )


def _log_restore_operation(
    *,
    backup_record: BackupCatalogRecord,
    restore_scope: RestoreScopeDefinition,
    pre_restore_backup: BackupResult,
    restored_tables: list[str],
    actor_name: str | None,
) -> None:
    from app.services import dangerous_operation_service

    restored_point = backup_record.restore_point_at.isoformat()
    summary = f"从备份 {backup_record.filename} 恢复{restore_scope.label}"
    impact_scope = {
        "backup_name": backup_record.filename,
        "restored_from": str(backup_record.path),
        "restore_scope": restore_scope.key,
        "restore_scope_label": restore_scope.label,
        "restore_point_at": restored_point,
        "restored_tables": restored_tables,
    }

    with SessionLocal() as db:
        dangerous_operation_service.log_dangerous_operation(
            db,
            operation_key="restore_backup",
            object_type=restore_scope.object_type,
            actor_name=actor_name,
            source="api",
            confirmation_phrase=dangerous_operation_service.RESTORE_BACKUP_CONFIRMATION,
            summary=summary,
            impact_scope=impact_scope,
            backup_path=pre_restore_backup.backup_path,
            extra_data={
                "restore_scope": restore_scope.key,
                "restore_scope_label": restore_scope.label,
                "backup_name": backup_record.filename,
                "restore_point_at": restored_point,
                "restored_tables": restored_tables,
            },
        )
        db.commit()


def _validate_restore_dependencies(connection: sqlite3.Connection, restore_scope: RestoreScopeDefinition) -> None:
    if restore_scope.key == "training_records":
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sessions",
            source_column="athlete_id",
            target_table="athletes",
            dependency_label="运动员",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sessions",
            source_column="assignment_id",
            target_table="athlete_plan_assignments",
            dependency_label="计划分配",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sessions",
            source_column="template_id",
            target_table="training_plan_templates",
            dependency_label="训练模板",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_session_items",
            source_column="template_item_id",
            target_table="training_plan_template_items",
            dependency_label="模板动作项",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_session_items",
            source_column="exercise_id",
            target_table="exercises",
            dependency_label="动作",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sync_conflicts",
            source_column="athlete_id",
            target_table="athletes",
            dependency_label="运动员",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sync_conflicts",
            source_column="assignment_id",
            target_table="athlete_plan_assignments",
            dependency_label="计划分配",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sync_issues",
            source_column="athlete_id",
            target_table="athletes",
            dependency_label="运动员",
        )
        _ensure_reference_ids_exist(
            connection,
            source_table="training_sync_issues",
            source_column="assignment_id",
            target_table="athlete_plan_assignments",
            dependency_label="计划分配",
        )
        return

    if restore_scope.key == "test_records":
        _ensure_reference_ids_exist(
            connection,
            source_table="test_records",
            source_column="athlete_id",
            target_table="athletes",
            dependency_label="运动员",
        )


def _replace_table_data_from_backup(connection: sqlite3.Connection, table_name: str) -> bool:
    if not _table_exists(connection, "main", table_name):
        raise bad_request(f"当前数据库缺少表：{table_name}")

    source_exists = _table_exists(connection, "restore_source", table_name)
    target_columns = _get_table_columns(connection, "main", table_name)

    connection.execute(f'DELETE FROM main.{_quote_identifier(table_name)}')

    if not source_exists:
        return False

    source_columns = _get_table_columns(connection, "restore_source", table_name)
    source_column_names = {column["name"] for column in source_columns}
    common_columns = [column["name"] for column in target_columns if column["name"] in source_column_names]
    if not common_columns:
        return False

    missing_required_columns = [
        column["name"]
        for column in target_columns
        if column["name"] not in source_column_names
        and column["notnull"]
        and column["default"] is None
    ]
    if missing_required_columns:
        joined_columns = "、".join(missing_required_columns[:5])
        raise bad_request(f"备份文件过旧，无法恢复表 {table_name}；缺少必填字段：{joined_columns}")

    columns_sql = ", ".join(_quote_identifier(column_name) for column_name in common_columns)
    connection.execute(
        f"INSERT INTO main.{_quote_identifier(table_name)} ({columns_sql}) "
        f"SELECT {columns_sql} FROM restore_source.{_quote_identifier(table_name)}"
    )
    return True


def _ensure_reference_ids_exist(
    connection: sqlite3.Connection,
    *,
    source_table: str,
    source_column: str,
    target_table: str,
    dependency_label: str,
) -> None:
    if not _table_exists(connection, "restore_source", source_table):
        return

    source_table_sql = _quote_identifier(source_table)
    source_column_sql = _quote_identifier(source_column)
    target_table_sql = _quote_identifier(target_table)
    rows = connection.execute(
        f"""
        SELECT DISTINCT source.{source_column_sql}
        FROM restore_source.{source_table_sql} AS source
        LEFT JOIN main.{target_table_sql} AS target
            ON target.id = source.{source_column_sql}
        WHERE source.{source_column_sql} IS NOT NULL
          AND target.id IS NULL
        ORDER BY source.{source_column_sql}
        LIMIT 5
        """
    ).fetchall()
    if not rows:
        return

    sample_ids = "、".join(str(row[0]) for row in rows)
    raise bad_request(
        f"当前数据库缺少备份内引用的{dependency_label}，不能只恢复该类数据。"
        f"缺失示例 ID：{sample_ids}。建议先补回基础数据或改用整库恢复。"
    )


def _table_exists(connection: sqlite3.Connection, schema_name: str, table_name: str) -> bool:
    row = connection.execute(
        f"SELECT 1 FROM {schema_name}.sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_table_columns(connection: sqlite3.Connection, schema_name: str, table_name: str) -> list[dict]:
    rows = connection.execute(
        f'PRAGMA {schema_name}.table_info("{table_name}")'
    ).fetchall()
    return [
        {
            "name": row[1],
            "notnull": bool(row[3]),
            "default": row[4],
        }
        for row in rows
    ]


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'
