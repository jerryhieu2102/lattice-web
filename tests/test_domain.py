from sqlalchemy import create_engine, inspect
from lattice_core.db import Base
import lattice_core.models  # noqa: F401


def test_all_domain_entities_exist():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    assert set(inspect(engine).get_table_names()) == {
        "actors",
        "auth_sessions",
        "permissions",
        "documents",
        "document_blocks",
        "financial_facts",
        "funding_sources",
        "obligations",
        "transfer_routes",
        "plans",
        "plan_allocations",
        "scenario_runs",
        "scenario_results",
        "intervention_candidates",
        "prepared_actions",
        "audit_events",
        "life_events",
    }
