from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from sqlalchemy.engine import make_url


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import (
    Athlete,
    AthletePlanAssignment,
    Exercise,
    Sport,
    Team,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
    User,
)


EXPECTED_DB_NAME = "tmp_e2e_training_offline_draft.db"
E2E_PASSWORD = "e2e-password-123"


def require_e2e_database() -> Path:
    database_url = get_settings().database_url
    try:
        url = make_url(database_url)
    except Exception as exc:
        raise SystemExit(f"Refusing to seed invalid database URL: {database_url}") from exc

    if url.drivername.split("+", 1)[0] != "sqlite":
        raise SystemExit(f"Refusing to seed non-SQLite database: {database_url}")

    if not url.database:
        raise SystemExit(f"Refusing to seed SQLite database without file path: {database_url}")

    db_path = Path(url.database)
    if db_path.name != EXPECTED_DB_NAME:
        raise SystemExit(f"Refusing to seed non-E2E database path: {db_path} from {database_url}")

    return db_path


def get_or_create_user(db, username: str, display_name: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        username=username,
        display_name=display_name,
        role_code="admin",
        password_hash=get_password_hash(E2E_PASSWORD),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_sport(db) -> Sport:
    sport = db.query(Sport).filter(Sport.code == "E2E_SPORT").first()
    if sport:
        return sport
    sport = Sport(name="E2E Sport", code="E2E_SPORT", notes="Playwright E2E only")
    db.add(sport)
    db.flush()
    return sport


def get_or_create_team(db, sport: Sport) -> Team:
    team = db.query(Team).filter(Team.sport_id == sport.id, Team.code == "E2E_TEAM").first()
    if team:
        return team
    team = Team(sport_id=sport.id, name="E2E Team", code="E2E_TEAM", notes="Playwright E2E only")
    db.add(team)
    db.flush()
    return team


def get_or_create_athlete(db, *, sport: Sport, team: Team, code: str, name: str) -> Athlete:
    athlete = db.query(Athlete).filter(Athlete.code == code).first()
    if athlete:
        return athlete
    athlete = Athlete(
        sport_id=sport.id,
        team_id=team.id,
        code=code,
        full_name=name,
        gender="unknown",
        is_active=True,
    )
    db.add(athlete)
    db.flush()
    return athlete


def get_or_create_exercise(db, *, code: str, name: str, user: User) -> Exercise:
    exercise = db.query(Exercise).filter(Exercise.code == code).first()
    if exercise:
        return exercise
    exercise = Exercise(
        name=name,
        code=code,
        source_type="e2e_seed",
        level1_category="E2E",
        level2_category="Offline draft",
        category_path="E2E / Offline draft",
        visibility="public",
        created_by_user_id=user.id,
    )
    db.add(exercise)
    db.flush()
    return exercise


def create_template(db, *, user: User, sport: Sport, team: Team, exercises: list[Exercise]) -> TrainingPlanTemplate:
    existing = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.name == "E2E Offline Draft Template").first()
    if existing:
        return existing

    template = TrainingPlanTemplate(
        name="E2E Offline Draft Template",
        description="Playwright E2E template",
        sport_id=sport.id,
        team_id=team.id,
        created_by=user.id,
        visibility="public",
        owner_user_id=None,
        created_by_user_id=user.id,
        is_active=True,
    )
    db.add(template)
    db.flush()

    module = TrainingPlanTemplateModule(
        template_id=template.id,
        sort_order=1,
        title="E2E Main",
        note="Two movements, two sets each",
    )
    db.add(module)
    db.flush()

    for index, exercise in enumerate(exercises, start=1):
        db.add(
            TrainingPlanTemplateItem(
                template_id=template.id,
                module_id=module.id,
                exercise_id=exercise.id,
                sort_order=index,
                prescribed_sets=2,
                prescribed_reps=5,
                target_note="E2E target",
                is_main_lift=index == 1,
                enable_auto_load=False,
                initial_load_mode="fixed_weight",
                initial_load_value=40 + index * 10,
                progression_goal=None,
                progression_rules={},
                ai_adjust_enabled=False,
            )
        )
    db.flush()
    return template


def ensure_assignment(db, *, athlete: Athlete, template: TrainingPlanTemplate, target_date: date) -> AthletePlanAssignment:
    assignment = (
        db.query(AthletePlanAssignment)
        .filter(
            AthletePlanAssignment.athlete_id == athlete.id,
            AthletePlanAssignment.template_id == template.id,
            AthletePlanAssignment.assigned_date == target_date,
        )
        .first()
    )
    if assignment:
        return assignment
    assignment = AthletePlanAssignment(
        athlete_id=athlete.id,
        template_id=template.id,
        assigned_date=target_date,
        start_date=target_date,
        end_date=target_date,
        repeat_weekdays=[1, 2, 3, 4, 5, 6, 7],
        status="active",
        notes="Playwright E2E assignment",
    )
    db.add(assignment)
    db.flush()
    return assignment


def main() -> None:
    db_path = require_e2e_database()
    print(f"[E2E_SEED] Seeding {db_path}")
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "e2e_admin", "E2E Admin")
        sport = get_or_create_sport(db)
        team = get_or_create_team(db, sport)
        normal_athlete = get_or_create_athlete(db, sport=sport, team=team, code="E2E_NORMAL", name="E2E Normal Athlete")
        offline_athlete = get_or_create_athlete(db, sport=sport, team=team, code="E2E_OFFLINE", name="E2E Offline Athlete")
        exercises = [
            get_or_create_exercise(db, code="E2E_SQUAT", name="E2E Squat", user=user),
            get_or_create_exercise(db, code="E2E_PRESS", name="E2E Press", user=user),
        ]
        template = create_template(db, user=user, sport=sport, team=team, exercises=exercises)
        target_date = date.today()
        ensure_assignment(db, athlete=normal_athlete, template=template, target_date=target_date)
        ensure_assignment(db, athlete=offline_athlete, template=template, target_date=target_date)
        db.commit()
        print("[E2E_SEED] Done")
        print(f"[E2E_SEED] Login username=e2e_admin password={E2E_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
