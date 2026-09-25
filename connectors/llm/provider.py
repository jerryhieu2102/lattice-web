from typing import Protocol
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class FactProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["amount", "currency", "due_date", "beneficiary", "available_from", "type", "status"]
    raw_value: str
    normalized_value: str
    confidence: float = Field(ge=0, le=1)
    evidence_text: str
    page: int = Field(ge=1)
    block_index: int = Field(ge=0)


class LLMProvider(Protocol):
    """Output-only adapter. Implementations receive no DB, tools, auth, or action capabilities."""

    def interpret_life_event(self, text: str, clock: str, locale: str = "en") -> dict: ...
    def classify_document(self, text: str) -> str: ...
    def extract_financial_facts(self, blocks: list[dict]) -> list[FactProposal]: ...
    def parse_financial_intent(self, text: str) -> dict: ...
    def explain_plan(self, summary: dict) -> str: ...
    def generate_benchmark_document(self, truth: dict) -> str: ...
