from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lattice_core.currencies import Currency, precise_amount


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Login(Input):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class DocumentInput(Input):
    filename: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=100000)
    trust_level: Literal["T2", "T3", "T4"] = "T3"
    target_obligation_id: str | None = None


class Confirmation(Input):
    confirmed: Literal[True]


class FundingInput(Input):
    label: str = Field(min_length=1, max_length=160)
    source_type: Literal["STUDENT_BALANCE", "PARENT_SUPPORT", "SCHOLARSHIP", "EMERGENCY_RESERVE", "OTHER"]
    amount: float = Field(ge=0, le=1000000000)
    currency: Currency
    available_from: date
    availability_status: Literal["AVAILABLE", "PLANNED", "EXPECTED", "CONDITIONAL", "LOCKED", "DISPUTED"]
    restriction_type: Literal["UNRESTRICTED", "EMERGENCY", "TUITION_ONLY"] = "UNRESTRICTED"
    minimum_remaining_balance: float = Field(ge=0, default=0)
    confirmation_note: str = Field(min_length=8, max_length=1000)

    @model_validator(mode="after")
    def reserve(self):
        precise_amount(self.amount, self.currency)
        precise_amount(self.minimum_remaining_balance, self.currency)
        if self.minimum_remaining_balance > self.amount:
            raise ValueError("Reserve exceeds funds")
        if self.source_type == "SCHOLARSHIP" and self.availability_status == "PLANNED":
            raise ValueError("Unreceived scholarship must remain EXPECTED or CONDITIONAL")
        return self


class FundingPatch(Input):
    amount: float | None = Field(default=None, ge=0, le=1000000000)
    available_from: date | None = None
    availability_status: (
        Literal["AVAILABLE", "PLANNED", "EXPECTED", "CONDITIONAL", "LOCKED", "DISPUTED"] | None
    ) = None
    confirmation_note: str = Field(min_length=8, max_length=1000)


class ObligationInput(Input):
    label: str = Field(min_length=1, max_length=160)
    type: Literal["TUITION", "HOUSING_DEPOSIT", "RENT", "INSURANCE", "OTHER"]
    beneficiary: str = Field(pattern=r"^[A-Z0-9_-]{3,80}$")
    amount: float = Field(gt=0, le=1000000000)
    currency: Currency
    due_date: date
    priority: Literal["CRITICAL", "HIGH", "NORMAL", "OPTIONAL"]
    partial_payment_allowed: bool = False
    minimum_payment: float = Field(default=0, ge=0)
    confirmation_note: str = Field(min_length=8, max_length=1000)

    @model_validator(mode="after")
    def payment(self):
        precise_amount(self.amount, self.currency)
        precise_amount(self.minimum_payment, self.currency)
        if self.minimum_payment > self.amount:
            raise ValueError("Minimum payment exceeds amount")
        return self


class ObligationPatch(Input):
    amount: float | None = Field(default=None, gt=0, le=1000000000)
    due_date: date | None = None
    confirmation_note: str = Field(min_length=8, max_length=1000)


class RouteInput(Input):
    provider_name: str = Field(min_length=1, max_length=160)
    from_currency: Currency
    to_currency: Currency
    fixed_fee: float = Field(ge=0)
    percentage_fee: float = Field(ge=0, lt=1)
    fx_rate: float = Field(gt=0, le=1000000)
    fx_markup: float = Field(ge=0, lt=1)
    min_transfer: float = Field(ge=0)
    max_transfer: float = Field(gt=0, le=1000000000)
    settlement_p50_days: int = Field(ge=0, le=30)
    settlement_p95_days: int = Field(ge=0, le=60)

    @model_validator(mode="after")
    def bounds(self):
        if self.min_transfer > self.max_transfer or self.settlement_p50_days > self.settlement_p95_days:
            raise ValueError("Invalid route bounds")
        return self


class ScenarioInput(Input):
    plan_id: str | None = None
    scenario: Literal["NORMAL", "TRANSFER_DELAY", "FX_STRESS", "SCHOLARSHIP_DELAY", "COMBINED_STRESS"] = (
        "NORMAL"
    )
    transfer_delay: int = Field(ge=0, le=7, default=0)
    scholarship_delay: int = Field(ge=0, le=21, default=0)
    fx_shock: float = Field(ge=0, le=10, default=0)
    unexpected_expense: float = Field(ge=0, le=2000, default=0)
    funding_cancellation: list[str] = Field(default_factory=list, max_length=20)
    iterations: int = Field(ge=10, le=1000, default=1000)
    seed: int = Field(ge=0, le=2147483647, default=17)

    @model_validator(mode="after")
    def named_parameters(self):
        presets = {
            "TRANSFER_DELAY": {"transfer_delay": 4},
            "FX_STRESS": {"fx_shock": 5},
            "SCHOLARSHIP_DELAY": {"scholarship_delay": 14},
            "COMBINED_STRESS": {
                "transfer_delay": 4,
                "scholarship_delay": 14,
                "fx_shock": 5,
                "unexpected_expense": 300,
            },
        }
        for key, value in presets.get(self.scenario, {}).items():
            if key not in self.model_fields_set:
                setattr(self, key, value)
        return self


class PermissionInput(Input):
    target_actor_id: str
    resource_type: Literal["FUNDING", "OBLIGATION", "PLAN", "ACTION"]
    resource_id: str
    permission_type: Literal[
        "VIEW_SHARED_OBLIGATION",
        "VIEW_OWN_CONTRIBUTION",
        "APPROVE_OWN_FUNDS",
        "VIEW_PRIVATE_FINANCES",
        "APPROVE_PLAN",
        "APPROVE_ACTION",
    ]


class ActionInput(Input):
    type: Literal[
        "PARENT_FUNDING_REQUEST",
        "TUITION_PAYMENT",
        "ACTIVATE_INSTALLMENT",
        "SCHEDULE_TRANSFER",
        "APPLY_RESCUE",
    ]
    plan_id: str
    obligation_id: str | None = None
    funding_source_id: str | None = None
    candidate_id: str | None = None


class IntentInput(Input):
    text: str = Field(min_length=1, max_length=2000)


class BeneficiaryVerification(Input):
    beneficiary: str = Field(pattern=r"^[A-Z0-9_-]{3,80}$")
    repeat_beneficiary: str
    confirmation_note: str = Field(min_length=20, max_length=1000)

    @model_validator(mode="after")
    def same(self):
        if self.beneficiary != self.repeat_beneficiary:
            raise ValueError("Identifiers must match exactly")
        return self
