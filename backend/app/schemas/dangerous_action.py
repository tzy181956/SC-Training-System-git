from pydantic import BaseModel, Field


class DangerousActionConfirm(BaseModel):
    confirmed: bool = False
    actor_name: str | None = Field(default=None, max_length=120)
    confirmation_text: str | None = Field(default=None, max_length=80)


class DeleteTestRecordsBatchPayload(DangerousActionConfirm):
    record_ids: list[int] = Field(default_factory=list)


class DeleteTestRecordsByFilterPayload(DangerousActionConfirm):
    athlete_keyword: str | None = Field(default=None, max_length=120)
    metric_keyword: str | None = Field(default=None, max_length=120)
    test_type: str | None = Field(default=None, max_length=120)
