from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.test_definition import (
    TestDefinitionCatalogRead,
    TestMetricDefinitionCreate,
    TestMetricDefinitionRead,
    TestMetricDefinitionUpdate,
    TestTypeDefinitionCreate,
    TestTypeDefinitionRead,
    TestTypeDefinitionUpdate,
)
from app.services import access_control_service, dangerous_operation_service, test_definition_service


router = APIRouter(prefix="/test-definitions", tags=["test-definitions"])


@router.get("", response_model=TestDefinitionCatalogRead)
def get_test_definition_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return {
        "types": test_definition_service.list_test_type_definitions(
            db,
            visible_sport_id=access_control_service.resolve_visible_sport_id(current_user),
            include_system=access_control_service.is_admin(current_user),
        )
    }


@router.post("/types", response_model=TestTypeDefinitionRead)
def create_test_type_definition(
    payload: TestTypeDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_definition_service.create_test_type_definition(db, payload, current_user)


@router.patch("/types/{definition_id}", response_model=TestTypeDefinitionRead)
def update_test_type_definition(
    definition_id: int,
    payload: TestTypeDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_definition_service.update_test_type_definition(db, definition_id, payload, current_user)


@router.delete("/types/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_type_definition(
    definition_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除测试类型")
    test_definition_service.delete_test_type_definition(
        db,
        definition_id,
        current_user,
        actor_name=payload.actor_name or current_user.display_name,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/metrics", response_model=TestMetricDefinitionRead)
def create_test_metric_definition(
    payload: TestMetricDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_definition_service.create_test_metric_definition(db, payload, current_user)


@router.patch("/metrics/{definition_id}", response_model=TestMetricDefinitionRead)
def update_test_metric_definition(
    definition_id: int,
    payload: TestMetricDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_definition_service.update_test_metric_definition(db, definition_id, payload, current_user)


@router.delete("/metrics/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_metric_definition(
    definition_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除测试项目")
    test_definition_service.delete_test_metric_definition(
        db,
        definition_id,
        current_user,
        actor_name=payload.actor_name or current_user.display_name,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
