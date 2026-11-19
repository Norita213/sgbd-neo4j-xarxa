import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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
    age: int | None = Field(default=None, ge=0, le=120)
    zone: str
    email: str
    activities: list[str] = []

    @field_validator("name")
    @classmethod
    def valid_name(cls, v:str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("El nom no pot estar buit")
        return clean

    @field_validator("email")
    @classmethod
    def valid_email(cls, v:str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean:
            raise ValueError("Correu electrònic no vàlid")
        return clean


class LoginIn(BaseModel):
    email: str


# ---------- Persones ----------
class PersonUpdate(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    zone: str | None = None
    email: str | None = None
    activities: list[str] | None = None

    @field_validator("name")
    @classmethod
    def valid_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            raise ValueError("El nom no pot quedar buit")
        return clean

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Escriu un correu electrònic vàlid")
        return clean


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
    def fits_in_slots(self):
        # Les franges (Slot) van de les 8h a les 21h (l'última acaba a les 22h)
        if self.start_time.hour < 8 or self.start_time.hour + self.duration_hours > 22:
            raise ValueError("La quedada ha de ser entre les 8:00 i les 22:00")
        if self.date < dt.date.today():
            raise ValueError("La data de la quedada no pot ser passada")
        if not self.title.strip():
            raise ValueError("La quedada necessita un títol")
        return self
