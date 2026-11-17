"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

SHAPE = "orchestrator"
INVESTIGATOR_TOOLS = ["lookup_order", "lookup_refund_history", "compute_compensation"]


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        budget = Budget()
        trace = Trace(make_run_id(SHAPE, claim_id, seed))

        def done(status: str, amount: int = 0, reason: str | None = None) -> RunResult:
            trace.add("decision", {"status": status, "proposal_amount": amount, "reason": reason})
            return finish(conn, shape=SHAPE, claim_id=claim_id, seed=seed, status=status,
                          proposal_amount=amount, budget=budget, trace=trace, error_reason=reason)

        # Parent context: only the orchestrator sees it; it never goes into the handoff.
        claim = get_claim_view(conn, claim_id)
        budget.add_tool(tool_cost())
        if not claim["found"]:
            return done("failed", reason="unknown_claim")
        if not claim["order_id"]:
            return done("needs_info", reason="missing_order_id")

        # Allowlisted facts only (none needed: investigators read the order row themselves).
        handoff = make_handoff(
            request_id=f"REQ-{claim_id}",
            claim_id=claim_id,
            task="quote_from_order_row",
            facts={},
            allowed_tools=INVESTIGATOR_TOOLS,
        )
        trace.add("handoff", safe_dump(handoff))
        found = run_readonly_investigators(conn, budget, handoff, principal_id=claim["principal_id"])["tools"]
        order_view = found.get("lookup_order") or {}
        history = found.get("lookup_refund_history") or {}
        trace.add("investigator", {"order_visible": order_view.get("visible"),
                                   "order_reason": order_view.get("reason"),
                                   "refund_history": safe_dump(history)})
        if not order_view.get("visible"):
            return done("escalated", reason=order_view.get("reason"))

        # Quote comes from the order row via compute_compensation; ticket delay is ignored.
        quote = found["compute_compensation"]
        proposal = int(quote["amount_vnd"])
        trace.add("quote", safe_dump(quote))
        complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
        if proposal <= 0:
            return done("denied", reason=quote.get("reason"))

        # Full quote; the host subtracts earlier refunds on this order.
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        if not outcome["ok"]:
            return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
        return done("resolved", proposal)
    finally:
        conn.close()
