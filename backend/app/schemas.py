from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PAYMENT_TERMS = ("hour", "week", "month", "quarter_year", "half_year", "year")
SERVICE_STATUSES = ("active", "blocked", "deleted", "suspended", "prolong_wait")


def to_camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class AccountIn(APIModel):
    id: int
    email: str = Field(min_length=3, max_length=320)
    balance: int = Field(default=0, ge=0)
    withdraw_balance: int = Field(default=0, ge=0)
    total_replenished: int = Field(default=0, ge=0)
    bonus_balance: int = Field(default=0, ge=0)
    bonus_state: Literal["locked", "unlocked"] = "locked"


class ServiceIn(APIModel):
    id: int
    name: str = Field(pattern=r"^[A-Za-z0-9-]+$", max_length=100)
    owner_id: int
    payment_term: Literal["hour", "week", "month", "quarter_year", "half_year", "year"]
    auto_prolong: bool = False
    created_at: datetime
    expires_at: datetime
    status: Literal["active", "blocked", "deleted", "suspended", "prolong_wait"]
    price: int = Field(ge=0)

    @field_validator("created_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "ServiceIn":
        if self.expires_at < self.created_at:
            raise ValueError("expiresAt must be >= createdAt")
        return self


class TransactionIn(APIModel):
    id: int
    amount: int = Field(ge=0, le=1000)
    status: Literal["performed", "not_performed"]
    performed_at: datetime | None = None
    created_at: datetime
    type: Literal["prolong", "order"]
    service_id: int

    @field_validator("created_at", "performed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def perform_state_is_consistent(self) -> "TransactionIn":
        if self.status == "performed":
            if self.performed_at is None:
                raise ValueError("performed transaction requires performedAt")
            if self.performed_at < self.created_at:
                raise ValueError("performedAt must be >= createdAt")
        elif self.performed_at is not None:
            raise ValueError("not_performed transaction must have null performedAt")
        return self


class SnapshotIn(APIModel):
    accounts: list[AccountIn] = Field(default_factory=list)
    services: list[ServiceIn] = Field(default_factory=list)
    transactions: list[TransactionIn] = Field(default_factory=list)


class LoginIn(BaseModel):
    email: str
    password: str


class ThresholdsPatch(BaseModel):
    medium: float | None = Field(default=None, gt=0, lt=100)
    high: float | None = Field(default=None, gt=0, lt=100)

    model_config = ConfigDict(extra="forbid")


class ProbabilityPatch(BaseModel):
    midpoint: float | None = None
    steepness: float | None = Field(default=None, gt=0)
    floor: float | None = Field(default=None, ge=0, le=1)
    ceiling: float | None = Field(default=None, ge=0, le=1)

    model_config = ConfigDict(extra="forbid")


class MoneyPatch(BaseModel):
    balance_mitigation: float | None = Field(default=None, ge=0, le=1)
    include_withdraw_balance: bool | None = None

    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)


class SettingsPatch(BaseModel):
    weights: dict[str, float] | None = None
    thresholds: ThresholdsPatch | None = None
    probability: ProbabilityPatch | None = None
    money: MoneyPatch | None = None
    status_floors: dict[str, float] | None = None
    recompute_interval_sec: int | None = Field(default=None, ge=10, le=3600)

    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)
