from fastapi import APIRouter

from app.api.endpoints import assignments, athletes, auth, exercises, plans, sessions, tags, test_records, training_reports


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(athletes.router)
api_router.include_router(tags.router)
api_router.include_router(exercises.router)
api_router.include_router(plans.router)
api_router.include_router(assignments.router)
api_router.include_router(sessions.router)
api_router.include_router(test_records.router)
api_router.include_router(training_reports.router)
