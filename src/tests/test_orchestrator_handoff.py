"""Orchestrator (shape C): the handoff crosses the agent boundary sanitized, and the ticket never sets the money."""

import json
from pathlib import Path

from lab8.handoff import FACT_KEYS, READONLY_TOOLS
from lab8.shapes import SHAPES
from tests.conftest import BY_ID

run_orchestrator = SHAPES["orchestrator"]


def test_handoff_is_readonly_and_trace_has_no_secret_or_pii(public_db):
    # C-010 carries a parent secret, auth header, and an order with phone/address/internal note.
    claim = BY_ID["C-010"]
    result = run_orchestrator("C-010", seed=11, store_path=str(public_db))
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert trace["run_id"] == result.run_id

    handoffs = [e["payload"] for e in trace["events"] if e["kind"] == "handoff"]
    assert handoffs, "orchestrator must trace the sanitized handoff"
    for handoff in handoffs:
        assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
        assert set(handoff["facts"]) <= FACT_KEYS

    blob = json.dumps(trace, ensure_ascii=False)
    for text in [claim["ticket"], "parent_secret", "raw_headers", *claim["expected"]["forbid_substrings"]]:
        assert text not in blob


def test_ticket_overstating_delay_is_denied_on_seed_55(public_db):
    # C-002: ticket says 5 days late, order row says 2. Swarm trusts the ticket on seed 55; orchestrator must not.
    result = run_orchestrator("C-002", seed=55, store_path=str(public_db))
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
