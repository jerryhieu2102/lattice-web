from lattice_core.graph.service import graph
from tests.factories import state
from optimizer.model.solver import optimize


def test_graph_edges_preserve_evidence_and_timing():
    s = state()
    g = graph(s, optimize(s)["allocations"])
    assert len(g["nodes"]) == 3
    allocation = next(e for e in g["edges"] if e["data"]["type"] == "allocation")
    assert allocation["data"]["expected_arrival_date"] == "2026-09-16"
    assert allocation["data"]["verification_state"] == "VERIFIED"
