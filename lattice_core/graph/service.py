from optimizer.model.solver import verified, usable, coverage_for


def graph(state, allocations):
    nodes, edges = [], []
    coverage = {c["obligation_id"]: c for c in coverage_for(state, allocations)}
    owners = sorted({f["owner_actor_id"] for f in state["funding"]})
    for index, owner in enumerate(owners):
        nodes.append(
            {
                "id": owner,
                "type": "actor",
                "position": {"x": 0, "y": index * 170},
                "data": {"label": owner.title(), "state": "ACTOR"},
            }
        )
    for index, f in enumerate(state["funding"]):
        risk = (
            "BLOCKED"
            if not usable(f) or f["restriction_type"] == "EMERGENCY"
            else "VERIFIED"
            if verified(f)
            else "EXPECTED"
        )
        nodes.append(
            {
                "id": f["id"],
                "type": "funding",
                "position": {"x": 260, "y": index * 140},
                "data": {**f, "state": risk},
            }
        )
        edges.append(
            {
                "id": f"own-{f['id']}",
                "source": f["owner_actor_id"],
                "target": f["id"],
                "data": {"type": "ownership"},
                "label": "owns",
            }
        )
    for index, o in enumerate(state["obligations"]):
        nodes.append(
            {
                "id": o["id"],
                "type": "obligation",
                "position": {"x": 650, "y": index * 140},
                "data": {
                    **o,
                    "nominal_coverage": coverage.get(o["id"], {}).get("nominal", 0),
                    "on_time_verified_coverage": coverage.get(o["id"], {}).get("on_time_verified", 0),
                    "state": "BLOCKED"
                    if o.get("security_hold")
                    else "AT RISK"
                    if not o.get("beneficiary_verified")
                    or (allocations and coverage.get(o["id"], {}).get("on_time_verified", 0) < 1)
                    else "VERIFIED",
                },
            }
        )
    for index, a in enumerate(allocations):
        edges.append(
            {
                "id": f"allocation-{index}",
                "source": a["funding_source_id"],
                "target": a["obligation_id"],
                "label": f"{a['destination_amount']:,.2f} {a['currency']}",
                "data": {
                    **a,
                    "type": "allocation",
                    "risk_state": a["status"],
                    "verification_state": a["status"],
                },
            }
        )
    return {"nodes": nodes, "edges": edges}
