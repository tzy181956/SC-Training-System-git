from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import sqrt

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import (
    Athlete,
    ScoreDimension,
    ScoreDimensionMetric,
    ScoreProfile,
    Team,
    TestMetricDefinition,
    TestRecord,
    User,
)
from app.schemas.score_profile import (
    ScoreAthleteResultRead,
    ScoreCalculationRequest,
    ScoreCalculationResponse,
    ScoreDimensionResultRead,
    ScoreMetricBreakdownRead,
    ScoreProfileCreate,
    ScoreProfileRead,
    ScoreProfileUpdate,
    ScoreTeamAverageDimensionRead,
)
from app.services import access_control_service, backup_service, dangerous_operation_service


def list_score_profiles(db: Session, user: User) -> list[ScoreProfile]:
    visible_sport_id = access_control_service.resolve_visible_sport_id(user)
    query = db.query(ScoreProfile).options(
        joinedload(ScoreProfile.dimensions)
        .joinedload(ScoreDimension.metrics)
        .joinedload(ScoreDimensionMetric.test_metric_definition)
        .joinedload(TestMetricDefinition.test_type)
    )
    if visible_sport_id is not None:
        query = query.filter(ScoreProfile.sport_id == visible_sport_id)
    return query.order_by(ScoreProfile.name.asc(), ScoreProfile.id.asc()).all()


def get_score_profile(db: Session, user: User, profile_id: int) -> ScoreProfile:
    profile = _query_score_profile(db).filter(ScoreProfile.id == profile_id).first()
    if not profile:
        raise not_found("评分模板不存在")
    _ensure_profile_access(user, profile)
    return profile


def create_score_profile(db: Session, payload: ScoreProfileCreate, user: User) -> ScoreProfile:
    sport_id = _resolve_profile_sport_id(user, payload.sport_id)
    if not str(payload.name or "").strip():
        raise bad_request("评分模板名称不能为空。")
    if not payload.dimensions:
        raise bad_request("至少需要一个能力维度。")

    _ensure_profile_name_unique(db, sport_id=sport_id, name=payload.name.strip())
    _validate_dimensions_payload(db, payload.dimensions, sport_id=sport_id)

    try:
        profile = ScoreProfile(
            name=payload.name.strip(),
            sport_id=sport_id,
            team_id=None,
            notes=(payload.notes or "").strip() or None,
            is_active=bool(payload.is_active),
        )
        db.add(profile)
        db.flush()
        _sync_profile_dimensions(db, profile, payload.dimensions)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise bad_request(f"保存评分模板失败：{exc.__class__.__name__}") from exc
    return get_score_profile(db, user, profile.id)


def update_score_profile(db: Session, profile_id: int, payload: ScoreProfileUpdate, user: User) -> ScoreProfile:
    profile = get_score_profile(db, user, profile_id)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise bad_request("评分模板名称不能为空。")
        _ensure_profile_name_unique(db, sport_id=profile.sport_id, name=name, exclude_id=profile.id)
        profile.name = name
    if payload.notes is not None:
        profile.notes = (payload.notes or "").strip() or None
    if payload.is_active is not None:
        profile.is_active = bool(payload.is_active)
    try:
        if payload.dimensions is not None:
            if not payload.dimensions:
                raise bad_request("至少需要保留一个能力维度。")
            _validate_dimensions_payload(db, payload.dimensions, sport_id=profile.sport_id)
            _sync_profile_dimensions(db, profile, payload.dimensions)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise bad_request(f"保存评分模板失败：{exc.__class__.__name__}") from exc
    return get_score_profile(db, user, profile.id)


def delete_score_profile(db: Session, profile_id: int, user: User, *, actor_name: str | None = None) -> None:
    profile = get_score_profile(db, user, profile_id)
    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_score_profile_{profile_id}")
    db.delete(profile)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_score_profile",
        object_type="score_profile",
        object_id=profile_id,
        actor_name=actor_name,
        summary=f"删除评分模板“{profile.name}”",
        impact_scope={
            "profile_name": profile.name,
            "sport_id": profile.sport_id,
            "dimension_count": len(profile.dimensions or []),
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def calculate_scores(db: Session, payload: ScoreCalculationRequest, user: User) -> ScoreCalculationResponse:
    team = access_control_service.get_accessible_team(db, user, payload.team_id)
    profile = get_score_profile(db, user, payload.score_profile_id)
    if profile.sport_id not in {None, team.sport_id}:
        raise bad_request("评分模板与所选队伍项目不一致。")
    if payload.date_from > payload.date_to:
        raise bad_request("开始日期不能晚于结束日期。")

    athletes = (
        db.query(Athlete)
        .options(joinedload(Athlete.team))
        .filter(Athlete.team_id == team.id, Athlete.is_active.is_(True))
        .order_by(Athlete.full_name.asc(), Athlete.id.asc())
        .all()
    )
    if not athletes:
        raise bad_request("当前队伍没有可参与评分的运动员。")

    metric_definitions = _collect_profile_metric_definitions(profile)
    if not metric_definitions:
        raise bad_request("评分模板中没有可用测试项目。")

    scoped_latest_records = _load_latest_records_for_scope(
        db,
        athlete_ids=[athlete.id for athlete in athletes],
        metric_names={definition.name for definition in metric_definitions.values()},
        date_from=payload.date_from,
        date_to=payload.date_to,
    )

    historical_records = {}
    if payload.baseline_mode == "historical_pool":
        historical_records = _load_historical_records_for_team(
            db,
            team_id=team.id,
            metric_names={definition.name for definition in metric_definitions.values()},
        )

    metric_baselines = _build_metric_baselines(
        payload=payload,
        athletes=athletes,
        metric_definitions=metric_definitions,
        scoped_latest_records=scoped_latest_records,
        historical_records=historical_records,
    )

    athlete_results: list[ScoreAthleteResultRead] = []
    all_warnings: list[str] = []
    for athlete in athletes:
        result = _score_athlete(
            athlete=athlete,
            profile=profile,
            scoped_latest_records=scoped_latest_records,
            metric_baselines=metric_baselines,
        )
        athlete_results.append(result)
        all_warnings.extend(result.warnings)

    athlete_results.sort(key=lambda item: (item.overall_score is None, -(item.overall_score or -9999), item.athlete_name))

    team_average_dimensions = _build_team_average_dimensions(profile, athlete_results)
    all_warnings.extend(
        warning
        for baseline in metric_baselines.values()
        for warning in baseline["warnings"]
    )

    return ScoreCalculationResponse(
        score_mode="Z 分数标准化评分",
        baseline_mode=payload.baseline_mode,
        baseline_label="当前批次" if payload.baseline_mode == "current_batch" else "历史数据池",
        score_explanation="50 表示参考数据平均水平，每 10 分约等于 1 个标准差；分数未做截断。",
        profile=ScoreProfileRead.model_validate(profile),
        ranking=athlete_results,
        team_average_dimensions=team_average_dimensions,
        warnings=list(dict.fromkeys(all_warnings)),
    )


def _query_score_profile(db: Session):
    return db.query(ScoreProfile).options(
        joinedload(ScoreProfile.dimensions)
        .joinedload(ScoreDimension.metrics)
        .joinedload(ScoreDimensionMetric.test_metric_definition)
        .joinedload(TestMetricDefinition.test_type)
    )


def _ensure_profile_access(user: User, profile: ScoreProfile) -> None:
    visible_sport_id = access_control_service.resolve_visible_sport_id(user)
    if visible_sport_id is not None and profile.sport_id != visible_sport_id:
        raise bad_request("无权访问该评分模板。")


def _resolve_profile_sport_id(user: User, requested_sport_id: int | None) -> int | None:
    if access_control_service.is_admin(user):
        return requested_sport_id
    return access_control_service.ensure_sport_bound_user(user)


def _ensure_profile_name_unique(db: Session, *, sport_id: int | None, name: str, exclude_id: int | None = None) -> None:
    query = db.query(ScoreProfile.id).filter(ScoreProfile.sport_id == sport_id, ScoreProfile.name == name)
    if exclude_id is not None:
        query = query.filter(ScoreProfile.id != exclude_id)
    if query.first():
        raise bad_request("当前项目下已存在同名评分模板。")


def _validate_dimensions_payload(db: Session, dimensions, *, sport_id: int | None) -> None:
    dimension_names = set()
    metric_definition_ids = set()
    for dimension in dimensions:
        name = str(dimension.name or "").strip()
        if not name:
            raise bad_request("能力维度名称不能为空。")
        if name in dimension_names:
            raise bad_request("同一模板中能力维度名称不能重复。")
        dimension_names.add(name)
        if not dimension.metrics:
            raise bad_request(f"能力维度“{name}”至少需要一个测试项目。")
        local_metric_ids = set()
        for metric in dimension.metrics:
            if metric.test_metric_definition_id in local_metric_ids:
                raise bad_request(f"能力维度“{name}”中存在重复测试项目。")
            local_metric_ids.add(metric.test_metric_definition_id)
            metric_definition_ids.add(metric.test_metric_definition_id)

    definitions = (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type))
        .filter(TestMetricDefinition.id.in_(metric_definition_ids))
        .all()
    )
    definition_map = {item.id: item for item in definitions}
    for metric_definition_id in metric_definition_ids:
        definition = definition_map.get(metric_definition_id)
        if not definition:
            raise bad_request("评分模板中包含不存在的测试项目。")
        definition_sport_id = definition.test_type.sport_id if definition.test_type else None
        if sport_id is not None and definition_sport_id not in {None, sport_id}:
            raise bad_request("评分模板中包含不属于当前项目可见范围的测试项目。")


def _sync_profile_dimensions(db: Session, profile: ScoreProfile, dimensions_payload) -> None:
    existing_dimensions = {item.id: item for item in profile.dimensions}
    next_dimensions: list[ScoreDimension] = []

    for dimension_payload in dimensions_payload:
        dimension = existing_dimensions.get(dimension_payload.id) if dimension_payload.id else None
        if dimension is None:
            dimension = ScoreDimension()
        dimension.name = dimension_payload.name.strip()
        dimension.sort_order = dimension_payload.sort_order
        dimension.weight = float(dimension_payload.weight or 1.0)

        existing_metrics = {item.id: item for item in dimension.metrics}
        next_metrics: list[ScoreDimensionMetric] = []
        for metric_payload in dimension_payload.metrics:
            metric = existing_metrics.get(metric_payload.id) if metric_payload.id else None
            if metric is None:
                metric = ScoreDimensionMetric()
            metric.test_metric_definition_id = metric_payload.test_metric_definition_id
            metric.weight = float(metric_payload.weight or 1.0)
            metric.sort_order = metric_payload.sort_order
            next_metrics.append(metric)

        dimension.metrics = next_metrics
        next_dimensions.append(dimension)

    profile.dimensions = next_dimensions
    db.flush()


def _collect_profile_metric_definitions(profile: ScoreProfile) -> dict[int, TestMetricDefinition]:
    definitions: dict[int, TestMetricDefinition] = {}
    for dimension in profile.dimensions:
        for metric in dimension.metrics:
            if metric.test_metric_definition:
                definitions[metric.test_metric_definition_id] = metric.test_metric_definition
    return definitions


def _load_latest_records_for_scope(
    db: Session,
    *,
    athlete_ids: list[int],
    metric_names: set[str],
    date_from: date,
    date_to: date,
):
    records = (
        db.query(TestRecord)
        .filter(
            TestRecord.athlete_id.in_(athlete_ids),
            TestRecord.metric_name.in_(metric_names),
            TestRecord.test_date >= date_from,
            TestRecord.test_date <= date_to,
        )
        .order_by(TestRecord.test_date.desc(), TestRecord.id.desc())
        .all()
    )
    latest: dict[tuple[int, str], TestRecord] = {}
    for record in records:
        key = (record.athlete_id, record.metric_name)
        if key not in latest:
            latest[key] = record
    return latest


def _load_historical_records_for_team(db: Session, *, team_id: int, metric_names: set[str]):
    records = (
        db.query(TestRecord)
        .join(TestRecord.athlete)
        .filter(Athlete.team_id == team_id, TestRecord.metric_name.in_(metric_names))
        .order_by(TestRecord.test_date.desc(), TestRecord.id.desc())
        .all()
    )
    grouped: dict[str, list[TestRecord]] = defaultdict(list)
    for record in records:
        grouped[record.metric_name].append(record)
    return grouped


def _build_metric_baselines(*, payload, athletes, metric_definitions, scoped_latest_records, historical_records):
    baselines = {}
    athlete_ids = {athlete.id for athlete in athletes}
    for definition in metric_definitions.values():
        if payload.baseline_mode == "current_batch":
            sample_records = [
                scoped_latest_records[key]
                for key in scoped_latest_records
                if key[0] in athlete_ids and key[1] == definition.name
            ]
        else:
            sample_records = historical_records.get(definition.name, [])

        values = [float(record.result_value) for record in sample_records]
        warnings: list[str] = []
        mean = None
        sd = None
        if len(values) < 6:
            warnings.append(f"{definition.name} 样本量不足，未参与评分。")
        else:
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
            sd = sqrt(variance) if variance >= 0 else 0
            if not sd:
                warnings.append(f"{definition.name} 数据无离散度，未参与评分。")
                sd = None

        baselines[definition.id] = {
            "definition": definition,
            "records": sample_records,
            "count": len(values),
            "mean": mean,
            "sd": sd,
            "warnings": warnings,
        }
    return baselines


def _score_athlete(*, athlete, profile, scoped_latest_records, metric_baselines):
    dimension_results: list[ScoreDimensionResultRead] = []
    athlete_warnings: list[str] = []
    missing_metrics: list[str] = []

    for dimension in profile.dimensions:
        metric_breakdowns: list[ScoreMetricBreakdownRead] = []
        valid_metric_entries: list[tuple[ScoreMetricBreakdownRead, float]] = []
        dimension_warnings: list[str] = []

        for metric_link in dimension.metrics:
            baseline = metric_baselines.get(metric_link.test_metric_definition_id)
            definition = baseline["definition"]
            record = scoped_latest_records.get((athlete.id, definition.name))
            warning_messages = list(baseline["warnings"])
            breakdown = ScoreMetricBreakdownRead(
                metric_definition_id=definition.id,
                metric_name=definition.name,
                test_type_name=definition.test_type.name if definition.test_type else "",
                is_lower_better=definition.is_lower_better,
                raw_value=float(record.result_value) if record else None,
                raw_test_date=record.test_date if record else None,
                mean=round(baseline["mean"], 4) if baseline["mean"] is not None else None,
                sd=round(baseline["sd"], 4) if baseline["sd"] is not None else None,
                weight=float(metric_link.weight),
                is_missing=record is None,
                sample_insufficient=baseline["count"] < 6,
                zero_variance=baseline["count"] >= 6 and baseline["sd"] is None,
                warnings=warning_messages,
            )

            if record is None:
                missing_metrics.append(f"{dimension.name} / {definition.name}")
                metric_breakdowns.append(breakdown)
                continue
            if baseline["count"] < 6 or baseline["sd"] is None or baseline["mean"] is None:
                metric_breakdowns.append(breakdown)
                continue

            value = float(record.result_value)
            z = (baseline["mean"] - value) / baseline["sd"] if definition.is_lower_better else (value - baseline["mean"]) / baseline["sd"]
            standard_score = 50 + 10 * z
            breakdown.z = round(z, 4)
            breakdown.standard_score = round(standard_score, 4)
            if abs(z) > 3:
                breakdown.outlier_warning = True
                breakdown.warnings.append("该项目 Z 分数绝对值大于 3，请关注是否存在极端表现或原始数据异常。")
            valid_metric_entries.append((breakdown, float(metric_link.weight or 0)))
            metric_breakdowns.append(breakdown)

        dimension_score = None
        if valid_metric_entries:
            total_weight = sum(weight for _, weight in valid_metric_entries)
            if total_weight <= 0:
                total_weight = float(len(valid_metric_entries))
                valid_metric_entries = [(entry, 1.0) for entry, _ in valid_metric_entries]
            dimension_score = sum((entry.standard_score or 0) * (weight / total_weight) for entry, weight in valid_metric_entries)
            dimension_score = round(dimension_score, 4)
            for entry, weight in valid_metric_entries:
                entry.weight = round(weight / total_weight, 4)
        else:
            dimension_warnings.append(f"{dimension.name} 当前没有可用于评分的有效项目。")

        dimension_results.append(
            ScoreDimensionResultRead(
                dimension_id=dimension.id,
                dimension_name=dimension.name,
                score=dimension_score,
                metrics=metric_breakdowns,
                warnings=dimension_warnings,
            )
        )
        athlete_warnings.extend(dimension_warnings)

    valid_dimension_scores = [item.score for item in dimension_results if item.score is not None]
    overall_score = round(sum(valid_dimension_scores) / len(valid_dimension_scores), 4) if valid_dimension_scores else None
    return ScoreAthleteResultRead(
        athlete_id=athlete.id,
        athlete_name=athlete.full_name,
        team_id=athlete.team_id,
        team_name=athlete.team.name if athlete.team else None,
        overall_score=overall_score,
        dimension_scores=dimension_results,
        missing_metrics=missing_metrics,
        warnings=list(dict.fromkeys(athlete_warnings)),
    )


def _build_team_average_dimensions(profile: ScoreProfile, athlete_results: list[ScoreAthleteResultRead]) -> list[ScoreTeamAverageDimensionRead]:
    results: list[ScoreTeamAverageDimensionRead] = []
    for dimension in profile.dimensions:
        scores = [
            dimension_result.score
            for athlete_result in athlete_results
            for dimension_result in athlete_result.dimension_scores
            if dimension_result.dimension_id == dimension.id and dimension_result.score is not None
        ]
        average_score = round(sum(scores) / len(scores), 4) if scores else None
        results.append(
            ScoreTeamAverageDimensionRead(
                dimension_id=dimension.id,
                dimension_name=dimension.name,
                score=average_score,
            )
        )
    return results
