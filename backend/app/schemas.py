from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from .messages import build_customer_messages

SQLiteInt = Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]
MoneyCents = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1,
    description='Whole JSON integer eurocents only; strings, booleans, decimal/exponent literals (100.0, 1e2) are rejected.')]

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
    id: SQLiteInt
    email: str = Field(min_length=3, max_length=320)
    balance: MoneyCents
    withdraw_balance: MoneyCents
    total_replenished: MoneyCents
    bonus_balance: MoneyCents
    bonus_state: Literal["locked", "unlocked"]


class ServiceIn(APIModel):
    id: SQLiteInt
    name: str = Field(pattern=r"^[A-Za-z0-9-]+$", max_length=100)
    owner_id: SQLiteInt
    payment_term: Literal["hour", "week", "month", "quarter_year", "half_year", "year"]
    auto_prolong: bool
    created_at: datetime
    expires_at: datetime
    status: Literal["active", "blocked", "deleted", "suspended", "prolong_wait"]
    price: MoneyCents

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
    id: SQLiteInt
    amount: MoneyCents
    status: Literal["performed", "not_performed"]
    performed_at: datetime | None = None
    created_at: datetime
    type: Literal["prolong", "order"]
    service_id: SQLiteInt

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
    """Full replacement: all arrays and required fields must be explicit; 0/false are valid."""
    accounts: list[AccountIn]
    services: list[ServiceIn]
    transactions: list[TransactionIn]


class LoginIn(BaseModel):
    email: str
    password: str


class ThresholdsPatch(BaseModel):
    medium: FiniteFloat | None = Field(default=None, gt=0, lt=100)
    high: FiniteFloat | None = Field(default=None, gt=0, lt=100)

    model_config = ConfigDict(extra="forbid")


class ProbabilityPatch(BaseModel):
    midpoint: FiniteFloat | None = Field(default=None, description="Any finite midpoint; values outside 0–100 are supported.")
    steepness: FiniteFloat | None = Field(default=None, gt=0)
    floor: FiniteFloat | None = Field(default=None, ge=0, le=1)
    ceiling: FiniteFloat | None = Field(default=None, ge=0, le=1)

    model_config = ConfigDict(extra="forbid")


class MoneyPatch(BaseModel):
    balance_mitigation: FiniteFloat | None = Field(default=None, ge=0, le=1)
    include_withdraw_balance: bool | None = None

    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)


class SettingsPatch(BaseModel):
    """Optional null/omitted fields do not change values. All numeric values must be finite.

    The merged configuration must satisfy medium < high, floor < ceiling and have
    a positive weight. These cross-field constraints are enforced by the API.
    """
    expected_version: int | None = Field(default=None, strict=True, ge=1)
    weights: dict[str, FiniteFloat] | None = None
    thresholds: ThresholdsPatch | None = None
    probability: ProbabilityPatch | None = None
    money: MoneyPatch | None = None
    status_floors: dict[str, FiniteFloat] | None = None
    recompute_interval_sec: int | None = Field(default=None, ge=10, le=3600)

    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)


class RuleExplanation(APIModel):
    """Score points rounded to one decimal; delta=round(afterScore-beforeScore,1).

    Real effects hidden by rounding remain with delta=0 and an explanatory label.
    Intermediate bonus scores may exceed100; the final customer score may not.
    """
    code: Literal["status_floor", "stale_status_floor", "customer_bonus", "score_cap"]
    scope: Literal["service", "customer"]
    service_id: SQLiteInt | None
    label: str
    before_score: FiniteFloat
    after_score: FiniteFloat
    delta: FiniteFloat
    related_service_ids: list[SQLiteInt]


class DriverOut(APIModel):
    code: str
    label: str
    contribution: FiniteFloat
    value: FiniteFloat | None = None


class ServiceOut(APIModel):
    id: SQLiteInt
    name: str
    price: FiniteFloat
    payment_term: str
    status: str
    auto_prolong: bool
    created_at: str
    expires_at: str
    score: FiniteFloat = Field(ge=0, le=100)
    level: Literal["high", "medium", "low", "unknown"]
    confidence: FiniteFloat
    stale_status: bool
    drivers: list[DriverOut]
    values: dict[str, FiniteFloat | None]
    expiry_days: FiniteFloat
    explanation_rules: list[RuleExplanation]


class MoneyOut(APIModel):
    amount_at_risk: FiniteFloat
    expected_loss: FiniteFloat
    covered_loss: FiniteFloat
    coverage: FiniteFloat
    mitigation: FiniteFloat


class EmailDraftOut(APIModel):
    situation: Literal["prolong_wait", "blocked", "suspended", "funds_gap", "expiry_auto_off", "unknown", "on_track"]
    situation_label: str
    subject: str
    body: str
    recipient: str
    service_id: SQLiteInt | None = None
    service_name: str | None = None


class CustomerDetailOut(APIModel):
    id: SQLiteInt
    email: str
    balance: FiniteFloat
    withdraw_balance: FiniteFloat
    bonus_balance: FiniteFloat
    bonus_state: Literal["locked", "unlocked"]
    total_replenished: FiniteFloat
    score: FiniteFloat | None = Field(ge=0, le=100)
    level: Literal["high", "medium", "low", "unknown"]
    confidence: FiniteFloat
    summary: str
    summary_details: list[str] = Field(default_factory=list)
    email_draft: EmailDraftOut | None = None
    drivers: list[DriverOut]
    services: list[ServiceOut]
    money: MoneyOut
    unknown_reason: str | None
    is_estimated: bool
    explanation_rules: list[RuleExplanation]


def _euros(cents: int | float) -> float:
    return round(float(cents) / 100.0, 2)


def detail_response(customer: dict[str, Any]) -> dict[str, Any]:
    # Старые сохранённые записи не содержат готовых текстов — собираем их из
    # имеющегося detail, чтобы карточка и письмо были одинаковыми для любых данных.
    messages = build_customer_messages(customer)
    services = []
    for service in customer["services"]:
        services.append(
            {
                **{k: v for k, v in service.items() if k != "priceCents"},
                "price": _euros(service["priceCents"]),
                "explanationRules": service.get("explanationRules", []),
            }
        )
    money = customer["money"]
    payload = {
        "id": customer["id"],
        "email": customer["email"],
        "balance": _euros(customer["balanceCents"]),
        "withdrawBalance": _euros(customer["withdrawCents"]),
        "bonusBalance": _euros(customer["bonusCents"]),
        "bonusState": customer["bonusState"],
        "totalReplenished": _euros(customer["totalReplenishedCents"]),
        "score": customer["score"],
        "level": customer["level"],
        "confidence": customer["confidence"],
        "summary": messages["summaryText"],
        "summaryDetails": messages["summaryDetails"],
        "emailDraft": messages["emailDraft"],
        "drivers": customer["drivers"],
        "explanationRules": customer.get("explanationRules", []),
        "services": services,
        "money": {
            "amountAtRisk": _euros(money["amountAtRiskCents"]),
            "expectedLoss": _euros(money["expectedLossCents"]),
            "coveredLoss": _euros(money["coveredLossCents"]),
            "coverage": money["coverage"],
            "mitigation": money["mitigation"],
        },
        "unknownReason": customer["unknownReason"],
        "isEstimated": customer["isEstimated"],
    }

    return CustomerDetailOut.model_validate(payload).model_dump(by_alias=True, exclude_unset=True)


class EffectiveThresholds(APIModel):
    medium: FiniteFloat
    high: FiniteFloat


class CalculationContext(APIModel):
    run_id: SQLiteInt
    settings_version: SQLiteInt
    thresholds: EffectiveThresholds


class SummaryBase(APIModel):
    counts_by_level: dict[str, int]
    total_customers: int
    scored_customers: int
    services_at_risk: int
    expected_loss: FiniteFloat
    amount_at_risk: FiniteFloat
    coverage: FiniteFloat
    aggregate_coverage: FiniteFloat
    underfunded_customers: int
    avg_score: FiniteFloat | None
    as_of: str
    updated_at: str
    currency: str


class SummaryOut(SummaryBase):
    calculation: CalculationContext


class CustomerListItemOut(APIModel):
    id: SQLiteInt
    email: str
    balance: FiniteFloat
    total_replenished: FiniteFloat
    score: FiniteFloat | None
    level: Literal['high', 'medium', 'low', 'unknown']
    expected_loss: FiniteFloat
    amount_at_risk: FiniteFloat
    services_at_risk: int


class CustomerPageOut(APIModel):
    items: list[CustomerListItemOut]
    total: int
    page: int
    page_size: int
    top_losses: list[CustomerListItemOut] = Field(max_length=5)
    summary: SummaryBase
    calculation: CalculationContext


class CustomerViewOut(CustomerDetailOut):
    calculation: CalculationContext
    as_of: str
    updated_at: str


class ForecastFactPoint(APIModel):
    date: str
    services: int
    customers: int


class ForecastPoint(APIModel):
    date: str
    services: int
    expected_non_renewals: FiniteFloat
    expected_loss: FiniteFloat


class ForecastTotals(APIModel):
    fact_services: int
    fact_customers: int
    forecast_services: int
    services_at_risk: int
    expected_non_renewals: FiniteFloat
    expected_loss: FiniteFloat


class ForecastOut(APIModel):
    as_of: str
    past_days: int
    horizon_days: int
    currency: str
    fact: list[ForecastFactPoint]
    forecast: list[ForecastPoint]
    totals: ForecastTotals
    note: str
