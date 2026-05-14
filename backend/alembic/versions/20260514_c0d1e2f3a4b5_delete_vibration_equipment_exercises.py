"""delete_vibration_equipment_exercises

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-05-14 16:35:00.000000

"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VIBRATION_EQUIPMENT_VALUE = "振动器材"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "exercises" not in table_names:
        return

    exercise_columns = {column["name"] for column in inspector.get_columns("exercises")}
    if "structured_tags" not in exercise_columns:
        return

    rows = bind.execute(
        sa.text("SELECT id, name, code, structured_tags FROM exercises")
    ).mappings().all()
    targets = [
        row
        for row in rows
        if _has_vibration_equipment(row["structured_tags"])
    ]
    if not targets:
        _log_noop(bind, table_names)
        return

    target_ids = [int(row["id"]) for row in targets]
    _assert_no_references(bind, table_names, target_ids)

    sample = [
        {"id": int(row["id"]), "name": row["name"], "code": row["code"]}
        for row in targets[:20]
    ]

    _delete_by_ids(bind, "exercise_tags", "exercise_id", target_ids, table_names)
    _delete_by_ids(bind, "exercises", "id", target_ids, table_names)

    _log_delete(bind, table_names, deleted_count=len(target_ids), sample=sample)


def downgrade() -> None:
    # Deleted actions cannot be reconstructed reliably from the remaining schema.
    # Restore the pre-migration backup if these actions are needed again.
    pass


def _has_vibration_equipment(structured_tags: object) -> bool:
    tags = _load_json_object(structured_tags)
    equipment = tags.get("equipment")
    if not isinstance(equipment, list):
        return False
    return any(str(value or "").strip() == VIBRATION_EQUIPMENT_VALUE for value in equipment)


def _load_json_object(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _assert_no_references(bind, table_names: set[str], target_ids: list[int]) -> None:
    for table_name in ("training_plan_template_items", "training_session_items"):
        if table_name not in table_names:
            continue
        count = _count_refs(bind, table_name, target_ids)
        if count:
            raise RuntimeError(
                f"Cannot delete vibration equipment exercises: {table_name} has {count} references."
            )


def _count_refs(bind, table_name: str, target_ids: list[int]) -> int:
    id_params = _id_params(target_ids)
    result = bind.execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE exercise_id IN ({', '.join(id_params.keys())})
            """
        ),
        {name.removeprefix(":"): value for name, value in id_params.items()},
    ).scalar()
    return int(result or 0)


def _delete_by_ids(bind, table_name: str, column_name: str, target_ids: list[int], table_names: set[str]) -> None:
    if table_name not in table_names:
        return
    id_params = _id_params(target_ids)
    bind.execute(
        sa.text(
            f"""
            DELETE FROM {table_name}
            WHERE {column_name} IN ({', '.join(id_params.keys())})
            """
        ),
        {name.removeprefix(":"): value for name, value in id_params.items()},
    )


def _id_params(target_ids: list[int]) -> dict[str, int]:
    return {f":id_{index}": value for index, value in enumerate(target_ids)}


def _log_delete(bind, table_names: set[str], *, deleted_count: int, sample: list[dict]) -> None:
    if "dangerous_operation_logs" not in table_names:
        return
    bind.execute(
        sa.text(
            """
            INSERT INTO dangerous_operation_logs (
                operation_key,
                object_type,
                object_id,
                actor_name,
                source,
                status,
                summary,
                impact_scope,
                confirmation_required,
                confirmation_phrase,
                backup_path,
                extra_data
            )
            VALUES (
                :operation_key,
                :object_type,
                NULL,
                :actor_name,
                :source,
                :status,
                :summary,
                :impact_scope,
                :confirmation_required,
                :confirmation_phrase,
                NULL,
                :extra_data
            )
            """
        ),
        {
            "operation_key": "delete_vibration_equipment_exercises",
            "object_type": "exercise_library",
            "actor_name": "Codex",
            "source": "migration",
            "status": "completed",
            "summary": f"批量删除 {deleted_count} 个带振动器材标签的动作",
            "impact_scope": json.dumps(
                {
                    "deleted_count": deleted_count,
                    "equipment_tag": VIBRATION_EQUIPMENT_VALUE,
                    "reference_check": {
                        "training_plan_template_items": 0,
                        "training_session_items": 0,
                    },
                    "sample": sample,
                },
                ensure_ascii=False,
            ),
            "confirmation_required": True,
            "confirmation_phrase": "确认删除392个带振动器材标签的动作，并以后导入时跳过振动器材动作",
            "extra_data": json.dumps(
                {
                    "rollback_note": "如需恢复，请使用迁移前自动备份恢复数据库。",
                },
                ensure_ascii=False,
            ),
        },
    )


def _log_noop(bind, table_names: set[str]) -> None:
    if "dangerous_operation_logs" not in table_names:
        return
    bind.execute(
        sa.text(
            """
            INSERT INTO dangerous_operation_logs (
                operation_key,
                object_type,
                object_id,
                actor_name,
                source,
                status,
                summary,
                impact_scope,
                confirmation_required,
                confirmation_phrase,
                backup_path,
                extra_data
            )
            VALUES (
                :operation_key,
                :object_type,
                NULL,
                :actor_name,
                :source,
                :status,
                :summary,
                :impact_scope,
                :confirmation_required,
                :confirmation_phrase,
                NULL,
                NULL
            )
            """
        ),
        {
            "operation_key": "delete_vibration_equipment_exercises",
            "object_type": "exercise_library",
            "actor_name": "Codex",
            "source": "migration",
            "status": "completed",
            "summary": "未发现带振动器材标签的动作，无需删除",
            "impact_scope": json.dumps({"deleted_count": 0}, ensure_ascii=False),
            "confirmation_required": True,
            "confirmation_phrase": "确认删除392个带振动器材标签的动作，并以后导入时跳过振动器材动作",
        },
    )
