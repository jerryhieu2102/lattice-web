from datetime import datetime, date, timezone
from uuid import uuid4
from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    Date,
    Numeric,
    Boolean,
    Float,
    Integer,
    JSON,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from lattice_core.db import Base


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)


class Timestamp:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Actor(Identity, Timestamp, Base):
    __tablename__ = "actors"
    type: Mapped[str] = mapped_column(String(24))
    role: Mapped[str] = mapped_column(String(24))
    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    relationship: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(3), default="VN")
    password_hash: Mapped[str] = mapped_column(Text)
    student_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AuthSession(Identity, Base):
    __tablename__ = "auth_sessions"
    actor_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Permission(Identity, Timestamp, Base):
    __tablename__ = "permissions"
    owner_actor_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    target_actor_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(36))
    permission_type: Mapped[str] = mapped_column(String(40))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Identity, Base):
    __tablename__ = "documents"
    owner_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    filename: Mapped[str] = mapped_column(String(240))
    document_type: Mapped[str] = mapped_column(String(40), default="UNKNOWN")
    trust_level: Mapped[str] = mapped_column(String(2), default="T3")
    status: Mapped[str] = mapped_column(String(30), default="UPLOADED")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sha256: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    security_flags: Mapped[list] = mapped_column(JSON, default=list)
    target_obligation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class DocumentBlock(Identity, Base):
    __tablename__ = "document_blocks"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    page: Mapped[int] = mapped_column(Integer)
    block_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class FinancialFact(Identity, Timestamp, Base):
    __tablename__ = "financial_facts"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    field: Mapped[str] = mapped_column(String(40))
    raw_value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str] = mapped_column(Text)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    verification_status: Mapped[str] = mapped_column(String(30), default="EXTRACTED")
    source_page: Mapped[int] = mapped_column(Integer)
    source_block: Mapped[str] = mapped_column(ForeignKey("document_blocks.id"))
    evidence_text: Mapped[str] = mapped_column(Text)


class FundingSource(Identity, Timestamp, Base):
    __tablename__ = "funding_sources"
    owner_actor_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    source_type: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(160))
    amount: Mapped[float] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(String(3))
    available_from: Mapped[date] = mapped_column(Date)
    availability_status: Mapped[str] = mapped_column(String(30))
    verification_status: Mapped[str] = mapped_column(String(30))
    restriction_type: Mapped[str] = mapped_column(String(30), default="UNRESTRICTED")
    minimum_remaining_balance: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    confidence: Mapped[float] = mapped_column(Float, default=1)
    source_fact_id: Mapped[str | None] = mapped_column(ForeignKey("financial_facts.id"), nullable=True)
    confirmation_note: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        CheckConstraint("amount >= 0"),
        CheckConstraint("minimum_remaining_balance >= 0 AND minimum_remaining_balance <= amount"),
    )


class Obligation(Identity, Timestamp, Base):
    __tablename__ = "obligations"
    owner_actor_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    type: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(160))
    beneficiary: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(String(3))
    due_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(20))
    partial_payment_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    minimum_payment: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    verification_status: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    budget_only: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    beneficiary_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    security_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    installment_option: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmation_note: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        CheckConstraint("amount > 0"),
        CheckConstraint("minimum_payment >= 0 AND minimum_payment <= amount"),
    )


class TransferRoute(Identity, Base):
    __tablename__ = "transfer_routes"
    provider_name: Mapped[str] = mapped_column(String(160))
    from_currency: Mapped[str] = mapped_column(String(3))
    to_currency: Mapped[str] = mapped_column(String(3))
    fixed_fee: Mapped[float] = mapped_column(Numeric(20, 4))
    percentage_fee: Mapped[float] = mapped_column(Numeric(12, 6))
    fx_rate: Mapped[float] = mapped_column(Numeric(20, 10))
    fx_markup: Mapped[float] = mapped_column(Numeric(12, 6))
    min_transfer: Mapped[float] = mapped_column(Numeric(20, 2))
    max_transfer: Mapped[float] = mapped_column(Numeric(20, 2))
    settlement_p50_days: Mapped[int] = mapped_column(Integer)
    settlement_p95_days: Mapped[int] = mapped_column(Integer)
    availability: Mapped[str] = mapped_column(String(20), default="AVAILABLE")
    verification_status: Mapped[str] = mapped_column(String(30), default="SOURCE_VERIFIED")
    __table_args__ = (
        CheckConstraint("fx_rate > 0"),
        CheckConstraint("fixed_fee >= 0 AND percentage_fee >= 0 AND percentage_fee < 1"),
        CheckConstraint("fx_markup >= 0 AND fx_markup < 1"),
        CheckConstraint("min_transfer >= 0 AND max_transfer >= min_transfer"),
        CheckConstraint("settlement_p95_days >= settlement_p50_days AND settlement_p50_days >= 0"),
    )


class Plan(Identity, Base):
    __tablename__ = "plans"
    student_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    objective_value: Mapped[float] = mapped_column(Float, default=0)
    total_estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    stress_failure_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    version: Mapped[int] = mapped_column(Integer)
    state_hash: Mapped[str] = mapped_column(String(64))
    summary: Mapped[dict] = mapped_column(JSON)
    snapshot: Mapped[dict] = mapped_column(JSON)


class PlanAllocation(Identity, Base):
    __tablename__ = "plan_allocations"
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    funding_source_id: Mapped[str] = mapped_column(ForeignKey("funding_sources.id"))
    obligation_id: Mapped[str] = mapped_column(ForeignKey("obligations.id"))
    transfer_route_id: Mapped[str] = mapped_column(ForeignKey("transfer_routes.id"))
    source_amount: Mapped[float] = mapped_column(Numeric(20, 4))
    destination_amount: Mapped[float] = mapped_column(Numeric(20, 4))
    scheduled_date: Mapped[date] = mapped_column(Date)
    expected_arrival_date: Mapped[date] = mapped_column(Date)
    estimated_fee: Mapped[float] = mapped_column(Numeric(20, 4))
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")


class ScenarioRun(Identity, Timestamp, Base):
    __tablename__ = "scenario_runs"
    student_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    parameters: Mapped[dict] = mapped_column(JSON)
    seed: Mapped[int] = mapped_column(Integer)
    iterations: Mapped[int] = mapped_column(Integer)


class ScenarioResult(Identity, Base):
    __tablename__ = "scenario_results"
    run_id: Mapped[str] = mapped_column(ForeignKey("scenario_runs.id"))
    result: Mapped[dict] = mapped_column(JSON)


class InterventionCandidate(Identity, Timestamp, Base):
    __tablename__ = "intervention_candidates"
    student_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    type: Mapped[str] = mapped_column(String(80))
    result: Mapped[dict] = mapped_column(JSON)


class PreparedAction(Identity, Timestamp, Base):
    __tablename__ = "prepared_actions"
    student_id: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    requested_by: Mapped[str] = mapped_column(ForeignKey("actors.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("actors.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(40))
    level: Mapped[str] = mapped_column(String(30), default="P2_PREPARE")
    status: Mapped[str] = mapped_column(String(20), default="PREPARED")
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    obligation_id: Mapped[str | None] = mapped_column(ForeignKey("obligations.id"), nullable=True)
    funding_source_id: Mapped[str | None] = mapped_column(ForeignKey("funding_sources.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    state_hash: Mapped[str] = mapped_column(String(64))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    sequence: Mapped[int] = mapped_column(Integer, unique=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    event_type: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("event_hash"),)


class LifeEvent(Identity, Timestamp, Base):
    __tablename__ = "life_events"
    actor_id: Mapped[str] = mapped_column(ForeignKey("actors.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(20), default="QUICK_CAPTURE")
    raw_input: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount_min_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount_max_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_window_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_window_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="OTHER")
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    essentiality: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    verification_status: Mapped[str] = mapped_column(String(30), default="REVIEW_REQUIRED")
    linked_funding_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("funding_sources.id"), nullable=True
    )
    linked_obligation_id: Mapped[str | None] = mapped_column(ForeignKey("obligations.id"), nullable=True)
    linked_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="CAPTURED")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint("amount_minor IS NULL OR amount_minor >= 0", name="life_amount_nonnegative"),
        CheckConstraint("amount_min_minor IS NULL OR amount_min_minor >= 0", name="life_min_nonnegative"),
        CheckConstraint(
            "amount_max_minor IS NULL OR amount_max_minor >= amount_min_minor", name="life_range_order"
        ),
    )
