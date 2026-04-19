from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import (
    AssignmentItemOverride,
    Athlete,
    AthletePlanAssignment,
    Exercise,
    ExerciseTag,
    Sport,
    Tag,
    Team,
    TestRecord,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    User,
)
from app.seed.seed_data import DEFAULT_EXERCISES, DEFAULT_TAGS
from app.services.load_prescription_service import build_assignment_item_override


def seed_demo_data(db: Session) -> None:
    """Populate a rich Chinese demo dataset for coach and training mode testing."""
    if db.query(User).first():
        return

    coach = User(username="coach", password_hash=get_password_hash("coach123"), display_name="陈教练", role_code="coach")
    training_user = User(username="training", password_hash=get_password_hash("training123"), display_name="训练模式", role_code="training")
    db.add_all([coach, training_user])
    db.flush()

    sports = _seed_sports_and_teams(db)
    athletes = _seed_athletes(db, sports)
    tags = _seed_tags(db)
    exercises = _seed_exercises(db, tags)
    templates = _seed_templates(db, coach.id, sports, exercises)
    _seed_test_records(db, athletes)
    _seed_assignments(db, athletes, templates)
    db.commit()


def _seed_sports_and_teams(db: Session) -> dict[str, dict]:
    basketball = Sport(name="篮球", code="basketball", notes="篮球专项示例数据")
    volleyball = Sport(name="排球", code="volleyball", notes="排球专项示例数据")
    db.add_all([basketball, volleyball])
    db.flush()

    teams = {
        "篮球一队": Team(name="篮球一队", code="basketball-first", sport_id=basketball.id, notes="成年组主力阵容"),
        "篮球二队": Team(name="篮球二队", code="basketball-second", sport_id=basketball.id, notes="轮换与发展阵容"),
        "排球青年队": Team(name="排球青年队", code="volleyball-youth", sport_id=volleyball.id, notes="青年后备队伍"),
    }
    db.add_all(teams.values())
    db.flush()

    return {
        "篮球": {"sport": basketball, "teams": {"一队": teams["篮球一队"], "二队": teams["篮球二队"]}},
        "排球": {"sport": volleyball, "teams": {"青年队": teams["排球青年队"]}},
    }


def _seed_athletes(db: Session, sports: dict[str, dict]) -> dict[str, Athlete]:
    athlete_rows = [
        ("王浩", "后卫", "中级", "爆发力好，适合速度力量训练。", "篮球", "一队"),
        ("赵磊", "前锋", "高级", "下肢力量基础较好。", "篮球", "一队"),
        ("李翔", "中锋", "高级", "需要关注髋部活动度。", "篮球", "一队"),
        ("陈宇", "后卫", "初级", "青少年运动员，优先稳定技术。", "篮球", "二队"),
        ("周宁", "锋卫摇摆", "中级", "上肢力量提升空间较大。", "篮球", "二队"),
        ("孙凯", "前锋", "中级", "需要补充核心稳定训练。", "篮球", "二队"),
        ("林晨", "主攻", "中级", "垂直弹跳优秀，力量基准待补。", "排球", "青年队"),
        ("高远", "副攻", "高级", "具备较强下肢力量。", "排球", "青年队"),
        ("许洋", "接应", "初级", "速度类训练优先。", "排球", "青年队"),
        ("彭雪", "二传", "中级", "需要强化肩部稳定。", "排球", "青年队"),
    ]

    athletes: dict[str, Athlete] = {}
    for full_name, position, level, notes, sport_name, team_name in athlete_rows:
        athlete = Athlete(
            user_id=None,
            sport_id=sports[sport_name]["sport"].id,
            team_id=sports[sport_name]["teams"][team_name].id,
            full_name=full_name,
            position=position,
            training_level=level,
            notes=notes,
        )
        db.add(athlete)
        athletes[full_name] = athlete

    db.flush()
    return athletes


def _seed_tags(db: Session) -> dict[str, Tag]:
    tags: dict[str, Tag] = {}
    for tag_data in DEFAULT_TAGS:
        tag = Tag(**tag_data)
        db.add(tag)
        tags[tag.code] = tag
    db.flush()
    return tags


def _seed_exercises(db: Session, tags: dict[str, Tag]) -> dict[str, Exercise]:
    exercises: dict[str, Exercise] = {}
    for entry in DEFAULT_EXERCISES:
        exercise = Exercise(**{key: value for key, value in entry.items() if key != "tag_codes"})
        db.add(exercise)
        db.flush()
        for code in entry["tag_codes"]:
            db.add(ExerciseTag(exercise_id=exercise.id, tag_id=tags[code].id))
        exercises[exercise.name] = exercise

    db.flush()
    return exercises


def _seed_templates(
    db: Session,
    coach_id: int,
    sports: dict[str, dict],
    exercises: dict[str, Exercise],
) -> dict[str, TrainingPlanTemplate]:
    templates: dict[str, TrainingPlanTemplate] = {}

    template_definitions = [
        {
            "name": "力量训练 A",
            "description": "下肢主项配合上肢推举的基础力量课。",
            "sport": "篮球",
            "team": "一队",
            "items": [
                _template_item(exercises["深蹲"], 1, 4, 5, "主项力量组，保持动作深度。", True, True, "percent_1rm", 82, 150, "力量", {"target_rir": 2, "up_step": 5, "down_step": 2.5, "miss_strategy": "降重一档", "fatigue_strategy": "连续两组吃力则停止加重"}, False),
                _template_item(exercises["卧推"], 2, 4, 6, "保持推举节奏，肩胛稳定。", True, True, "percent_1rm", 78, 120, "力量", {"target_rir": 2, "up_step": 2.5, "down_step": 2.5, "miss_strategy": "维持或小降", "fatigue_strategy": "连续吃力提醒技术检查"}, False),
                _template_item(exercises["平板支撑"], 3, 3, 45, "每组保持 45 秒。", False, False, "fixed_weight", 0, 60, "耐力", {"target_rir": 3, "up_step": 0, "down_step": 0, "miss_strategy": "缩短保持时间", "fatigue_strategy": "动作变形即停止"}, False),
            ],
        },
        {
            "name": "速度力量 B",
            "description": "强调快速发力与爆发输出。",
            "sport": "篮球",
            "team": "一队",
            "items": [
                _template_item(exercises["箱跳"], 1, 4, 4, "每次落地安静，保持爆发。", False, False, "fixed_weight", 0, 75, "速度", {"target_rir": 4, "up_step": 0, "down_step": 0, "miss_strategy": "降低箱高", "fatigue_strategy": "速度下降明显则减组"}, False),
                _template_item(exercises["药球胸前传"], 2, 5, 5, "每次全力快速出手。", False, False, "fixed_weight", 4, 60, "速度", {"target_rir": 4, "up_step": 1, "down_step": 1, "miss_strategy": "减轻药球重量", "fatigue_strategy": "保持动作速度优先"}, True),
                _template_item(exercises["保加利亚分腿蹲"], 3, 3, 8, "单腿控制稳定，前脚主动发力。", False, False, "fixed_weight", 20, 90, "力量", {"target_rir": 3, "up_step": 2.5, "down_step": 2.5, "miss_strategy": "每侧少 2 次", "fatigue_strategy": "保持动作质量"}, False),
            ],
        },
        {
            "name": "上肢辅助恢复",
            "description": "上肢力量与肩部稳定辅助课。",
            "sport": "篮球",
            "team": "二队",
            "items": [
                _template_item(exercises["哑铃推举"], 1, 4, 8, "肩胛稳定，不借腰。", False, False, "fixed_weight", 16, 90, "力量", {"target_rir": 3, "up_step": 2, "down_step": 2, "miss_strategy": "减少重量", "fatigue_strategy": "保持动作路径"}, False),
                _template_item(exercises["引体向上"], 2, 4, 6, "每次胸口主动找杆。", False, False, "fixed_weight", 0, 90, "力量", {"target_rir": 2, "up_step": 2.5, "down_step": 2.5, "miss_strategy": "改弹力带辅助", "fatigue_strategy": "最后一组留 1 次余力"}, False),
                _template_item(exercises["侧桥"], 3, 3, 30, "每侧保持 30 秒。", False, False, "fixed_weight", 0, 45, "稳定", {"target_rir": 4, "up_step": 0, "down_step": 0, "miss_strategy": "缩短时间", "fatigue_strategy": "出现代偿则结束"}, False),
            ],
        },
        {
            "name": "下肢爆发课",
            "description": "下肢爆发与后侧链强化组合。",
            "sport": "篮球",
            "team": "二队",
            "items": [
                _template_item(exercises["硬拉"], 1, 5, 3, "杠铃贴腿，干净起拉。", True, True, "percent_1rm", 85, 180, "力量", {"target_rir": 2, "up_step": 5, "down_step": 5, "miss_strategy": "降重后完成", "fatigue_strategy": "连续吃力进入回退组"}, False),
                _template_item(exercises["罗马尼亚硬拉"], 2, 3, 6, "控制离心，髋部后移。", False, False, "fixed_weight", 60, 120, "力量", {"target_rir": 3, "up_step": 5, "down_step": 5, "miss_strategy": "降低重量", "fatigue_strategy": "保持动作控制"}, False),
                _template_item(exercises["踝关节弹跳"], 3, 3, 20, "快速触地，保持节奏。", False, False, "fixed_weight", 0, 45, "速度", {"target_rir": 4, "up_step": 0, "down_step": 0, "miss_strategy": "减少次数", "fatigue_strategy": "节奏下降则结束"}, False),
            ],
        },
        {
            "name": "排球力量基础",
            "description": "排球青年队基础力量与核心稳定课。",
            "sport": "排球",
            "team": "青年队",
            "items": [
                _template_item(exercises["深蹲"], 1, 4, 4, "优先动作稳定，再追求重量。", True, True, "percent_1rm", 76, 150, "力量", {"target_rir": 3, "up_step": 2.5, "down_step": 2.5, "miss_strategy": "维持重量", "fatigue_strategy": "动作变形时停止"}, False),
                _template_item(exercises["哑铃推举"], 2, 3, 8, "肩部稳定，全程控制。", False, False, "fixed_weight", 14, 90, "力量", {"target_rir": 3, "up_step": 2, "down_step": 2, "miss_strategy": "减轻重量", "fatigue_strategy": "保持动作完整"}, False),
                _template_item(exercises["滑板腿弯举"], 3, 3, 10, "腘绳肌发力为主。", False, False, "fixed_weight", 0, 60, "耐力", {"target_rir": 3, "up_step": 0, "down_step": 0, "miss_strategy": "减少重复次数", "fatigue_strategy": "动作失控即结束"}, False),
            ],
        },
        {
            "name": "恢复与激活",
            "description": "比赛周恢复、激活和预康复模板。",
            "sport": "排球",
            "team": "青年队",
            "items": [
                _template_item(exercises["踝关节弹跳"], 1, 3, 15, "保持轻快节奏。", False, False, "fixed_weight", 0, 30, "速度", {"target_rir": 4, "up_step": 0, "down_step": 0, "miss_strategy": "减少次数", "fatigue_strategy": "动作慢下来就结束"}, False),
                _template_item(exercises["平板支撑"], 2, 3, 40, "每组稳定保持 40 秒。", False, False, "fixed_weight", 0, 45, "稳定", {"target_rir": 4, "up_step": 0, "down_step": 0, "miss_strategy": "缩短保持时间", "fatigue_strategy": "动作变形即结束"}, False),
                _template_item(exercises["侧桥"], 3, 3, 25, "每侧保持 25 秒。", False, False, "fixed_weight", 0, 45, "稳定", {"target_rir": 4, "up_step": 0, "down_step": 0, "miss_strategy": "缩短时间", "fatigue_strategy": "保持中立位"}, False),
            ],
        },
    ]

    for definition in template_definitions:
        template = TrainingPlanTemplate(
            name=definition["name"],
            description=definition["description"],
            sport_id=sports[definition["sport"]]["sport"].id,
            team_id=sports[definition["sport"]]["teams"][definition["team"]].id,
            created_by=coach_id,
            is_active=True,
        )
        db.add(template)
        db.flush()

        for item_payload in definition["items"]:
            db.add(TrainingPlanTemplateItem(template_id=template.id, **item_payload))

        db.flush()
        templates[template.name] = template

    return templates


def _seed_test_records(db: Session, athletes: dict[str, Athlete]) -> None:
    today = date.today()
    test_rows = [
        ("王浩", today - timedelta(days=20), "力量测试", "深蹲 1RM", 145, "公斤", "季前下肢力量测试"),
        ("王浩", today - timedelta(days=18), "力量测试", "卧推 1RM", 95, "公斤", "季前上肢力量测试"),
        ("赵磊", today - timedelta(days=22), "力量测试", "深蹲 1RM", 160, "公斤", "力量课基准"),
        ("赵磊", today - timedelta(days=20), "力量测试", "卧推 1RM", 102.5, "公斤", "卧推基准"),
        ("李翔", today - timedelta(days=21), "力量测试", "深蹲 1RM", 175, "公斤", "大个队员下肢基准"),
        ("李翔", today - timedelta(days=19), "力量测试", "硬拉 1RM", 205, "公斤", "后侧链力量基准"),
        ("陈宇", today - timedelta(days=16), "力量测试", "卧推 1RM", 72.5, "公斤", "青年队卧推基准"),
        ("周宁", today - timedelta(days=17), "力量测试", "硬拉 1RM", 155, "公斤", "后侧链力量测试"),
        ("孙凯", today - timedelta(days=15), "体能测试", "反向纵跳", 56, "厘米", "爆发能力测试"),
        ("林晨", today - timedelta(days=14), "体能测试", "反向纵跳", 61, "厘米", "弹跳表现优秀"),
        ("高远", today - timedelta(days=16), "力量测试", "深蹲 1RM", 150, "公斤", "排球专项力量测试"),
        ("高远", today - timedelta(days=14), "力量测试", "卧推 1RM", 87.5, "公斤", "上肢力量测试"),
        ("许洋", today - timedelta(days=13), "速度测试", "30 米冲刺", 4.36, "秒", "速度课基准"),
        ("彭雪", today - timedelta(days=12), "力量测试", "哑铃推举 6RM", 18, "公斤", "肩部稳定训练基准"),
    ]

    for athlete_name, test_date, test_type, metric_name, result_value, unit, notes in test_rows:
        db.add(
            TestRecord(
                athlete_id=athletes[athlete_name].id,
                test_date=test_date,
                test_type=test_type,
                metric_name=metric_name,
                result_value=result_value,
                unit=unit,
                notes=notes,
            )
        )

    db.flush()


def _seed_assignments(
    db: Session,
    athletes: dict[str, Athlete],
    templates: dict[str, TrainingPlanTemplate],
) -> None:
    today = date.today()
    start_date = today - timedelta(days=1)
    end_date = today + timedelta(days=10)

    assignment_rows = [
        ("王浩", "力量训练 A", start_date, end_date, "本周下肢主项计划"),
        ("王浩", "速度力量 B", today, end_date, "同日叠加爆发课"),
        ("赵磊", "力量训练 A", start_date, end_date, "锋线力量周期"),
        ("李翔", "力量训练 A", start_date, end_date, "中锋力量主周期"),
        ("陈宇", "上肢辅助恢复", start_date, today + timedelta(days=7), "青少年技术稳定优先"),
        ("周宁", "下肢爆发课", start_date, today + timedelta(days=7), "后侧链和爆发并行"),
        ("高远", "排球力量基础", start_date, end_date, "排球青年队力量基础"),
        ("高远", "恢复与激活", today, end_date, "比赛周恢复加练"),
        ("许洋", "恢复与激活", start_date, today + timedelta(days=5), "速度周轻量安排"),
    ]

    for athlete_name, template_name, current_start, current_end, notes in assignment_rows:
        template = templates[template_name]
        assignment = AthletePlanAssignment(
            athlete_id=athletes[athlete_name].id,
            template_id=template.id,
            assigned_date=current_start,
            start_date=current_start,
            end_date=current_end,
            status="active",
            notes=notes,
        )
        db.add(assignment)
        db.flush()

        for item in template.items:
            override = build_assignment_item_override(db, athletes[athlete_name].id, item)
            if override:
                db.add(
                    AssignmentItemOverride(
                        assignment_id=assignment.id,
                        template_item_id=override["template_item_id"],
                        initial_load_override=override["initial_load_override"],
                    )
                )

    db.flush()


def _template_item(
    exercise: Exercise,
    sort_order: int,
    prescribed_sets: int,
    prescribed_reps: int,
    target_note: str,
    is_main_lift: bool,
    enable_auto_load: bool,
    initial_load_mode: str,
    initial_load_value: float | int | None,
    rest_seconds: int,
    progression_goal: str,
    progression_rules: dict,
    ai_adjust_enabled: bool,
) -> dict:
    return {
        "exercise_id": exercise.id,
        "sort_order": sort_order,
        "prescribed_sets": prescribed_sets,
        "prescribed_reps": prescribed_reps,
        "target_note": target_note,
        "is_main_lift": is_main_lift,
        "enable_auto_load": enable_auto_load,
        "initial_load_mode": initial_load_mode,
        "initial_load_value": float(initial_load_value) if initial_load_value is not None else None,
        "rest_seconds": rest_seconds,
        "progression_goal": progression_goal,
        "progression_rules": progression_rules,
        "ai_adjust_enabled": ai_adjust_enabled,
    }
