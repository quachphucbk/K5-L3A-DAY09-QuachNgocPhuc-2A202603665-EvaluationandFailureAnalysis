"""Shape B: bounded single-agent read loop, host-owned refund."""
from __future__ import annotations

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace


def run_claim(claim_id: str, *, seed: int, store_path: str,
              crash_at: str | None = None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("single", claim_id, seed))
    conn = connect(store_path)
    try:
        claim = get_claim_view(conn, claim_id)
        budget.add_tool(tool_cost())
        trace.add("claim_read", {"found": claim.get("found", False), "claim_id": claim_id})

        def done(status: str, amount: int = 0, error: str | None = None) -> RunResult:
            trace.add("outcome", {"status": status, "proposal_amount": amount,
                                  "error_reason": error})
            return finish(conn, shape="single", claim_id=claim_id, seed=seed,
                          status=status, proposal_amount=amount, budget=budget,
                          trace=trace, error_reason=error)

        if not claim.get("found"):
            return done("failed", error="unknown_claim")
        if not claim.get("order_id"):
            return done("needs_info", error="missing_order_id")

        state = {"next": "lookup_order", "order": None, "quote": None}

        def decide(observation: dict) -> dict:
            last = observation.get("last_tool")
            result = observation.get("last_result") or {}
            if last == "lookup_order":
                if not result.get("visible"):
                    return {"final": {"status": "escalated", "reason": result.get("reason")}}
                state["order"] = result["order"]
                state["next"] = "lookup_policy"
            elif last == "lookup_policy":
                state["next"] = "lookup_refund_history"
            elif last == "lookup_refund_history":
                state["next"] = "compute_compensation"
            elif last == "compute_compensation":
                state["quote"] = result
                return {"final": {"status": "quoted", "amount_vnd": result.get("amount_vnd", 0)}}

            name = state["next"]
            # Mock model call accounts for simulated tokens and cost.
            complete(budget, seed=seed, purpose="route", prompt=name)
            trace.add("agent_tool", {"tool": name})
            if name == "lookup_order" or name == "lookup_refund_history":
                args = {"order_id": claim["order_id"], "principal_id": claim["principal_id"]}
            elif name == "compute_compensation":
                args = {"order": state["order"]}
            else:
                args = {}
            return {"tool": name, "args": args}

        loop = run_react(conn, budget, observation={"claim": {"claim_id": claim_id}},
                         decide=decide, max_steps=8)
        final = loop["final"]
        if loop["stopped"] != "final":
            return done("failed", error="step_cap")
        if final.get("status") == "escalated":
            return done("escalated", error=final.get("reason"))
        amount = int((state["quote"] or {}).get("amount_vnd", 0))
        trace.add("quote", {"amount_vnd": amount})
        if amount <= 0:
            return done("denied", amount, (state["quote"] or {}).get("reason"))

        # The host owns authorization, per-order cap, idempotency and the write.
        outcome = issue_refund(conn, claim_id, amount, crash_at=crash_at)
        trace.add("refund_host", {"ok": outcome["ok"], "reason": outcome["reason"]})
        if outcome.get("conflict"):
            return done("failed", amount, "amount_conflict")
        if not outcome["ok"]:
            return done("denied", amount, outcome["reason"])
        return done("resolved", amount)
    finally:
        conn.close()
