from fastapi import APIRouter

from app.api.endpoints import (
    assignments,
    athletes,
    auth,
    backups,
    exercise_categories,
    exercises,
    logs,
    monitoring,
    plans,
    sessions,
    tags,
    test_definitions,
    test_records,
    training_loads,
    training_reports,
    users,
)


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(athletes.router)
api_router.include_router(backups.router)
api_router.include_router(tags.router)
api_router.include_router(exercises.router)
api_router.include_router(exercise_categories.router)
api_router.include_router(logs.router)
api_router.include_router(monitoring.router)
api_router.include_router(plans.router)
api_router.include_router(assignments.router)
api_router.include_router(sessions.router)
api_router.include_router(test_definitions.router)
api_router.include_router(test_records.router)
api_router.include_router(training_reports.router)
api_router.include_router(training_loads.router)
api_router.include_router(users.router)
