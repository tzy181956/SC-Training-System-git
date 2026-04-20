from pydantic import BaseModel

from app.schemas.common import ORMModel


class SportBase(BaseModel):
    name: str
    code: str
    notes: str | None = None


class SportCreate(SportBase):
    pass


class SportRead(ORMModel, SportBase):
    id: int


class TeamBase(BaseModel):
    sport_id: int
    name: str
    code: str
    notes: str | None = None


class TeamCreate(TeamBase):
    pass


class TeamRead(ORMModel, TeamBase):
    id: int
    sport: SportRead | None = None


class AthleteBase(BaseModel):
    user_id: int | None = None
    sport_id: int | None = None
    team_id: int | None = None
    full_name: str
    position: str | None = None
    height: float | None = None
    weight: float | None = None
    body_fat_percentage: float | None = None
    wingspan: float | None = None
    standing_reach: float | None = None
    notes: str | None = None
    is_active: bool = True


class AthleteCreate(AthleteBase):
    pass


class AthleteUpdate(BaseModel):
    user_id: int | None = None
    sport_id: int | None = None
    team_id: int | None = None
    full_name: str | None = None
    position: str | None = None
    height: float | None = None
    weight: float | None = None
    body_fat_percentage: float | None = None
    wingspan: float | None = None
    standing_reach: float | None = None
    notes: str | None = None
    is_active: bool | None = None


class AthleteRead(ORMModel, AthleteBase):
    id: int
    sport: SportRead | None = None
    team: TeamRead | None = None
