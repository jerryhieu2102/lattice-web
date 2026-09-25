"""Independently validate both the cited evidence and the normalized value."""

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from lattice_core.currencies import CURRENCIES


def supported(proposal, blocks):
    if not proposal.evidence_text or not 0 <= proposal.block_index < len(blocks):
        return False
    block = blocks[proposal.block_index]
    if (
        proposal.evidence_text not in block["text"]
        or proposal.page != block.get("page", 1)
        or ":" not in proposal.evidence_text
    ):
        return False
    key, raw = proposal.evidence_text.split(":", 1)
    raw = raw.strip()
    if key.strip().lower().replace(" ", "_") != proposal.field or raw != proposal.raw_value:
        return False
    normalized = proposal.normalized_value
    try:
        if proposal.field == "amount":
            return (
                bool(re.fullmatch(r"\d{1,10}(?:\.\d{1,2})?", raw))
                and Decimal(raw).is_finite()
                and 0 < Decimal(raw) <= 1000000000
                and Decimal(normalized) == Decimal(raw)
            )
        if proposal.field in {"due_date", "available_from"}:
            return normalized == date.fromisoformat(raw).isoformat()
        if proposal.field == "currency":
            return normalized == raw and raw in CURRENCIES
        if proposal.field == "beneficiary":
            return normalized == raw and bool(re.fullmatch(r"[A-Z0-9_-]{3,80}", raw))
        return normalized == raw
    except (InvalidOperation, ValueError):
        return False
