import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Mateixos codis de dia que al graf
Day = Literal["Dl", "Dm", "Dc", "Dj", "Dv", "Ds", "Dg"]
DAYS: list[str] = ["Dl", "Dm", "Dc", "Dj", "Dv", "Ds", "Dg"]


class ActivityIn(BaseModel):
    name: str


class ZoneIn(BaseModel):
    name: str


class NearIn(BaseModel):
    zone_a: str
    zone_b: str


# ---------- Autenticació simulada (TODO) ----------
class RegisterIn(BaseModel):
    name: str
    age: int | None = Field(default=None, ge=0)
    zone: str
    email: str
    activities: list[str] = []


class LoginIn(BaseModel):
    email: str


# ---------- Persones ----------
class PersonUpdate(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=0)
    zone: str | None = None
    activities: list[str] | None = None


class SlotRange(BaseModel):
    """Rang d'hores senceres. 18 -> 20 crea les franges 18 i 19."""

    day: Day
    from_hour: int = Field(ge=0, le=23)
    to_hour: int = Field(ge=1, le=24, description="Hora final (exclosa)")

    @model_validator(mode="after")
    def end_after_start(self):
        if self.to_hour <= self.from_hour:
            raise ValueError("to_hour ha de ser més gran que from_hour")
        return self


class AvailabilityIn(BaseModel):
    slots: list[SlotRange]
    mode: Literal["available", "unavailable"] = Field(
        default="available",
        description="'unavailable' = els rangs són quan NO ets disponible (com a la maqueta); "
        "es calcula el complement dins de day_start..day_end",
    )
    day_start: int = Field(default=8, ge=0, le=23)
    day_end: int = Field(default=22, ge=1, le=24)


# ---------- Comunitats ----------
class CommunityIn(BaseModel):
    name: str
    activity: str
    zone: str
    creator_id: str


# ---------- Quedades ----------
class EventIn(BaseModel):
    organizer_id: str
    title: str
    activity: str
    zone: str
    date: dt.date
    start_time: dt.time
    duration_hours: int = Field(default=1, ge=1, le=8)
    place: str | None = None
    description: str | None = None
    capacity: int = Field(default=12, ge=2)
    community_id: str | None = None

    @model_validator(mode="after")
    def fits_in_day(self):
        if self.start_time.hour + self.duration_hours > 24:
            raise ValueError("La quedada no pot passar de mitjanit")
        return self
