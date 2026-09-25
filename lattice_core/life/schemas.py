"""Untrusted proposals deliberately contain no actor, status, trust or payment authority."""

from datetime import date
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator
from lattice_core.currencies import Currency, SCALE

EventType = Literal[
    "PURCHASE_INTENT",
    "EXPENSE_OCCURRED",
    "NEW_OBLIGATION",
    "OBLIGATION_CHANGED",
    "FUNDING_EXPECTED",
    "FUNDING_RECEIVED",
    "FUNDING_DELAYED",
    "FUNDING_REDUCED",
    "RECURRING_EXPENSE",
    "REFUND_EXPECTED",
    "REIMBURSEMENT_EXPECTED",
    "BORROWING",
    "LENDING",
    "TRANSFER_PENDING",
    "TRANSFER_FAILED",
    "TRAVEL_PLAN",
    "EDUCATION_EXPENSE",
    "HOUSING_EVENT",
    "HEALTH_EXPENSE",
    "FAMILY_SUPPORT",
    "SAVINGS_GOAL",
    "SECURITY_INCIDENT",
    "ACCOUNT_UNAVAILABLE",
    "FX_CONCERN",
    "EMERGENCY",
    "OTHER",
]
Minor = Annotated[int, Field(strict=True, ge=0, le=100_000_000_000)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class EnvelopeItem(Strict):
    category: Literal[
        "FLIGHT", "ACCOMMODATION", "LOCAL_TRANSPORT", "FOOD", "VISA", "INSURANCE", "ACTIVITIES", "BUFFER"
    ]
    amount_minor: Minor
    currency: Currency


class Proposal(Strict):
    event_type: EventType = "OTHER"
    mode: Literal["HYPOTHETICAL", "ACTUAL", "EXPECTED"] = "HYPOTHETICAL"
    title: str = Field(default="Life event", max_length=240)
    amount_minor: Minor | None = None
    amount_min_minor: Minor | None = None
    amount_max_minor: Minor | None = None
    currency: Currency | None = None
    event_date: date | None = None
    expected_date: date | None = None
    date_window_start: date | None = None
    date_window_end: date | None = None
    counterparty: str | None = Field(default=None, max_length=120)
    category: str = Field(default="OTHER", max_length=40)
    essentiality: Literal["ESSENTIAL", "DISCRETIONARY", "UNKNOWN"] = "UNKNOWN"
    priority: Literal["CRITICAL", "HIGH", "NORMAL", "OPTIONAL"] = "NORMAL"
    recurrence_rule: Literal["WEEKLY", "MONTHLY", "YEARLY"] | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    funding_source_id: str | None = Field(default=None, max_length=36)
    obligation_id: str | None = Field(default=None, max_length=36)
    delay_days: int | None = Field(default=None, ge=1, le=365)
    amount_is_delta: bool = False
    receivable_minor: Minor | None = None
    repayment_date: date | None = None
    repayment_minor: Minor | None = None
    envelope: list[EnvelopeItem] = Field(default_factory=list, max_length=8)
    security_flags: list[str] = Field(default_factory=list, max_length=10)
    question: bool = False

    @model_validator(mode="after")
    def coherent(self):
        if self.event_type in {"EMERGENCY", "HEALTH_EXPENSE"}:
            self.essentiality, self.priority = "ESSENTIAL", "CRITICAL"
        elif self.essentiality == "ESSENTIAL" and self.priority in {"NORMAL", "OPTIONAL"}:
            self.priority = "HIGH"
        if self.repayment_minor is not None and self.repayment_minor <= 0:
            raise ValueError("Repayment must be positive")
        if (
            self.receivable_minor is not None
            and self.event_type == "EXPENSE_OCCURRED"
            and self.amount_minor is not None
            and self.receivable_minor > self.amount_minor
        ):
            raise ValueError("Shared reimbursement cannot exceed the recorded bill")
        if self.amount_min_minor is not None or self.amount_max_minor is not None:
            if (
                self.amount_min_minor is None
                or self.amount_max_minor is None
                or self.amount_min_minor > self.amount_max_minor
            ):
                raise ValueError("Both bounds of an ordered amount range are required")
        if self.date_window_start and self.date_window_end and self.date_window_start > self.date_window_end:
            raise ValueError("Date window is reversed")
        if len({x.category for x in self.envelope}) != len(self.envelope):
            raise ValueError("Travel categories must be unique")
        if self.currency:
            for n in (self.amount_minor, self.amount_max_minor, self.receivable_minor, self.repayment_minor):
                if n is not None and n > 1_000_000_000 * SCALE[self.currency]:
                    raise ValueError("Amount exceeds supported limit")
        return self


class Capture(Strict):
    raw_input: str = Field(min_length=3, max_length=4000)
    locale: Literal["en", "vi", "zh"] = "en"
    amount_minor: Minor | None = None
    currency: Currency | None = None
    event_date: date | None = None


class Review(Strict):
    proposal: Proposal
    version: int = Field(ge=1)


class Confirm(Review):
    confirmed: Literal[True]
    confirmation_note: str = Field(min_length=8, max_length=1000)


class Version(Strict):
    version: int = Field(ge=1)


class Receipt(Version):
    confirmed: Literal[True]
    received_date: date
    confirmation_note: str = Field(min_length=8, max_length=1000)


class Resolve(Version):
    confirmed: Literal[True]
    confirmation_note: str = Field(min_length=8, max_length=1000)
