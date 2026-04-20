from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session, joinedload

from app.models import Athlete, TestRecord

TEMPLATE_HEADERS = [
    "运动员姓名",
    "测试日期",
    "测试类型",
    "测试项目",
    "数值结果",
    "显示文本",
    "单位",
    "备注",
]


@dataclass
class TestRecordImportSummary:
    total_rows: int
    imported_rows: int
    skipped_rows: int


def build_import_template_workbook(db: Session) -> bytes:
    athletes = (
        db.query(Athlete)
        .options(joinedload(Athlete.team), joinedload(Athlete.sport))
        .order_by(Athlete.full_name.asc())
        .all()
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "测试数据导入模板"
    sheet.append(TEMPLATE_HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    example_name = athletes[0].full_name if athletes else "示例运动员"
    sheet.append([example_name, "2026-03-14", "力量测试", "卧推", 55, "", "kg", "示例"])
    sheet.append([example_name, "2026-03-14", "耐力测试", "3000m", 812.3, "13′32″3", "s", "文本结果可选"])

    reference_sheet = workbook.create_sheet("运动员名单")
    reference_sheet.append(["运动员姓名", "队伍", "项目"])
    for cell in reference_sheet[1]:
        cell.font = Font(bold=True)
    for athlete in athletes:
        reference_sheet.append(
            [
                athlete.full_name,
                athlete.team.name if athlete.team else "",
                athlete.sport.name if athlete.sport else "",
            ]
        )

    instruction_sheet = workbook.create_sheet("填写说明")
    instruction_sheet.append(["字段", "说明"])
    for cell in instruction_sheet[1]:
        cell.font = Font(bold=True)
    instruction_sheet.append(["运动员姓名", "必须与系统中的运动员姓名完全一致"])
    instruction_sheet.append(["测试日期", "建议填写 YYYY-MM-DD，例如 2026-03-14"])
    instruction_sheet.append(["测试类型", "如 力量测试 / 体能测试 / 速度测试 / 耐力测试"])
    instruction_sheet.append(["测试项目", "如 卧推 / 深蹲 / 3000m"])
    instruction_sheet.append(["数值结果", "系统统计和图表使用该字段"])
    instruction_sheet.append(["显示文本", "可选，用于展示原始时间文本，如 13′32″3"])
    instruction_sheet.append(["单位", "如 kg / cm / s / 次 / RSI"])
    instruction_sheet.append(["备注", "可选"])

    return _workbook_to_bytes(workbook)


def build_test_record_library_workbook(db: Session) -> bytes:
    records = (
        db.query(TestRecord)
        .options(joinedload(TestRecord.athlete).joinedload(Athlete.team), joinedload(TestRecord.athlete).joinedload(Athlete.sport))
        .order_by(TestRecord.test_date.desc(), TestRecord.id.desc())
        .all()
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "测试数据总库"
    headers = [
        "记录ID",
        "运动员姓名",
        "项目",
        "队伍",
        "测试日期",
        "测试类型",
        "测试项目",
        "数值结果",
        "显示文本",
        "单位",
        "备注",
        "创建时间",
    ]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for record in records:
        athlete = record.athlete
        sheet.append(
            [
                record.id,
                athlete.full_name if athlete else "",
                athlete.sport.name if athlete and athlete.sport else "",
                athlete.team.name if athlete and athlete.team else "",
                record.test_date.isoformat(),
                record.test_type,
                record.metric_name,
                record.result_value,
                record.result_text or "",
                record.unit,
                record.notes or "",
                record.created_at.isoformat() if record.created_at else "",
            ]
        )

    return _workbook_to_bytes(workbook)


def import_test_records_from_workbook(db: Session, file_bytes: bytes) -> TestRecordImportSummary:
    workbook = load_workbook(BytesIO(file_bytes), data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in sheet[1]]
    header_index = {header: index for index, header in enumerate(headers)}

    missing_headers = [header for header in TEMPLATE_HEADERS if header not in header_index]
    if missing_headers:
        raise ValueError(f"导入模板缺少列: {', '.join(missing_headers)}")

    athletes = {athlete.full_name: athlete for athlete in db.query(Athlete).all()}
    existing_keys = {
        (
            record.athlete_id,
            record.test_date.isoformat(),
            record.test_type,
            record.metric_name,
            float(record.result_value),
            record.result_text or "",
            record.unit,
        )
        for record in db.query(TestRecord).all()
    }

    pending_records: list[TestRecord] = []
    errors: list[str] = []
    skipped_rows = 0
    total_rows = 0

    for row_number in range(2, sheet.max_row + 1):
        row_values = [sheet.cell(row_number, column).value for column in range(1, sheet.max_column + 1)]
        if all(value in (None, "") for value in row_values):
            continue

        total_rows += 1
        try:
            athlete_name = _string_cell(row_values[header_index["运动员姓名"]], required=True)
            athlete = athletes.get(athlete_name)
            if not athlete:
                raise ValueError(f"系统中不存在运动员: {athlete_name}")

            record_date = _parse_date(row_values[header_index["测试日期"]])
            test_type = _string_cell(row_values[header_index["测试类型"]], required=True)
            metric_name = _string_cell(row_values[header_index["测试项目"]], required=True)
            result_value = _float_cell(row_values[header_index["数值结果"]])
            result_text = _optional_string_cell(row_values[header_index["显示文本"]])
            unit = _string_cell(row_values[header_index["单位"]], required=True)
            notes = _optional_string_cell(row_values[header_index["备注"]])

            duplicate_key = (
                athlete.id,
                record_date.isoformat(),
                test_type,
                metric_name,
                result_value,
                result_text or "",
                unit,
            )
            if duplicate_key in existing_keys:
                skipped_rows += 1
                continue

            pending_records.append(
                TestRecord(
                    athlete_id=athlete.id,
                    test_date=record_date,
                    test_type=test_type,
                    metric_name=metric_name,
                    result_value=result_value,
                    result_text=result_text,
                    unit=unit,
                    notes=notes,
                )
            )
            existing_keys.add(duplicate_key)
        except ValueError as exc:
            errors.append(f"第 {row_number} 行: {exc}")

    if errors:
        raise ValueError("；".join(errors[:10]))

    if pending_records:
        db.add_all(pending_records)
        db.commit()

    return TestRecordImportSummary(
        total_rows=total_rows,
        imported_rows=len(pending_records),
        skipped_rows=skipped_rows,
    )


def _workbook_to_bytes(workbook: Workbook) -> bytes:
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream.getvalue()


def _string_cell(value: object, *, required: bool = False) -> str:
    text = str(value).strip() if value is not None else ""
    if required and not text:
        raise ValueError("存在必填字段为空")
    return text


def _optional_string_cell(value: object) -> str | None:
    text = _string_cell(value)
    return text or None


def _float_cell(value: object) -> float:
    if value is None or str(value).strip() == "":
        raise ValueError("数值结果不能为空")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"数值结果无法解析: {value}") from exc


def _parse_date(value: object) -> date:
    if value is None or str(value).strip() == "":
        raise ValueError("测试日期不能为空")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip().replace("/", "-").replace(".", "-")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"测试日期格式错误: {value}") from exc
