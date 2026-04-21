from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.schema_sync import ensure_runtime_schema


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup_sync_schema() -> None:
    ensure_runtime_schema()
    registered_paths = {route.path for route in app.routes}
    expected_paths = {
        f"{settings.api_prefix}/exercise-categories",
        f"{settings.api_prefix}/exercise-categories/tree",
    }
    missing_paths = sorted(expected_paths - registered_paths)
    if missing_paths:
        print(f"[STARTUP] Missing exercise category routes: {', '.join(missing_paths)}")
    else:
        print(f"[STARTUP] Exercise category routes registered: {', '.join(sorted(expected_paths))}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
