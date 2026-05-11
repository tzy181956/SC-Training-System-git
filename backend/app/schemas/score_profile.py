from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.test_definition import TestMetricDefinitionSummaryRead


class ScoreDimensionMetricWrite(BaseModel):
    id: int | None = None
    test_metric_definition_id: int
    weight: float = 1.0
    sort_order: int = 1


class ScoreDimensionWrite(BaseModel):
    id: int | None = None
    name: str
    sort_order: int = 1
    weight: float = 1.0
    metrics: list[ScoreDimensionMetricWrite] = Field(default_factory=list)


class ScoreProfileCreate(BaseModel):
    name: str
    sport_id: int | None = None
    team_id: int | None = None
    notes: str | None = None
    is_active: bool = True
    dimensions: list[ScoreDimensionWrite] = Field(default_factory=list)


class ScoreProfileUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    dimensions: list[ScoreDimensionWrite] | None = None


class ScoreDimensionMetricRead(ORMModel):
    id: int
    test_metric_definition_id: int
    weight: float
    sort_order: int
    test_metric_definition: TestMetricDefinitionSummaryRead


class ScoreDimensionRead(ORMModel):
    id: int
    name: str
    sort_order: int
    weight: float
    metrics: list[ScoreDimensionMetricRead] = Field(default_factory=list)


class ScoreProfileRead(ORMModel):
    id: int
    name: str
    sport_id: int | None = None
    team_id: int | None = None
    notes: str | None = None
    is_active: bool
    dimensions: list[ScoreDimensionRead] = Field(default_factory=list)


class ScoreMetricBreakdownRead(BaseModel):
    metric_definition_id: int
    metric_name: str
    test_type_name: str
    is_lower_better: bool
    raw_value: float | None = None
    raw_test_date: date | None = None
    mean: float | None = None
    sd: float | None = None
    z: float | None = None
    standard_score: float | None = None
    weight: float | None = None
    is_missing: bool = False
    sample_insufficient: bool = False
    zero_variance: bool = False
    outlier_warning: bool = False
    warnings: list[str] = Field(default_factory=list)


class ScoreDimensionResultRead(BaseModel):
    dimension_id: int
    dimension_name: str
    score: float | None = None
    metrics: list[ScoreMetricBreakdownRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ScoreAthleteResultRead(BaseModel):
    athlete_id: int
    athlete_name: str
    team_id: int | None = None
    team_name: str | None = None
    overall_score: float | None = None
    dimension_scores: list[ScoreDimensionResultRead] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ScoreTeamAverageDimensionRead(BaseModel):
    dimension_id: int
    dimension_name: str
    score: float | None = None


class ScoreCalculationRequest(BaseModel):
    score_profile_id: int
    team_id: int
    date_from: date
    date_to: date
    baseline_mode: Literal["current_batch", "historical_pool"]


class ScoreCalculationResponse(BaseModel):
    score_mode: str
    baseline_mode: Literal["current_batch", "historical_pool"]
    baseline_label: str
    score_explanation: str
    profile: ScoreProfileRead
    ranking: list[ScoreAthleteResultRead] = Field(default_factory=list)
    team_average_dimensions: list[ScoreTeamAverageDimensionRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
