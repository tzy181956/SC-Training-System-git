from datetime import date

from pydantic import BaseModel, computed_field, field_validator

from app.schemas.common import ORMModel


def _validate_birth_date(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("生日不能晚于今天")
    return value


def _calculate_age_from_birth_date(value: date | None) -> int | None:
    if value is None:
        return None

    today = date.today()
    age = today.year - value.year
    if (today.month, today.day) < (value.month, value.day):
        age -= 1
    return age if age >= 0 else None


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
    birth_date: date | None = None
    gender: str | None = None
    position: str | None = None
    height: float | None = None
    weight: float | None = None
    body_fat_percentage: float | None = None
    wingspan: float | None = None
    standing_reach: float | None = None
    notes: str | None = None
    is_active: bool = True

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        return _validate_birth_date(value)


class AthleteCreate(AthleteBase):
    code: str | None = None


class AthleteUpdate(BaseModel):
    user_id: int | None = None
    sport_id: int | None = None
    team_id: int | None = None
    code: str | None = None
    full_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    position: str | None = None
    height: float | None = None
    weight: float | None = None
    body_fat_percentage: float | None = None
    wingspan: float | None = None
    standing_reach: float | None = None
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        return _validate_birth_date(value)


class AthleteRead(ORMModel, AthleteBase):
    id: int
    code: str
    sport: SportRead | None = None
    team: TeamRead | None = None

    @computed_field(return_type=int | None)
    @property
    def age(self) -> int | None:
        return _calculate_age_from_birth_date(self.birth_date)
