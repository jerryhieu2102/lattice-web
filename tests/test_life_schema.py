import pytest
from pydantic import ValidationError
from lattice_core.life.schemas import Proposal
from lattice_core.models import LifeEvent


def test_life_model_has_private_minor_unit_storage():
    assert LifeEvent.__table__.c.actor_id.foreign_keys
    assert str(LifeEvent.__table__.c.amount_minor.type) == "BIGINT"


@pytest.mark.parametrize(
    "extra",
    [
        {"approved": True},
        {"actor_id": "father"},
        {"verification_status": "SOURCE_VERIFIED"},
        {"allocations": []},
    ],
)
def test_provider_cannot_propose_authority(extra):
    with pytest.raises(ValidationError):
        Proposal(**extra)


@pytest.mark.parametrize(
    "values",
    [
        {"amount_minor": -1},
        {"amount_minor": 1.5},
        {"amount_min_minor": 200, "amount_max_minor": 100},
        {"currency": "FAKE"},
    ],
)
def test_invalid_money_rejected(values):
    with pytest.raises(ValidationError):
        Proposal(**values)
