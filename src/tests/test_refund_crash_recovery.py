"""Top-up refunds must survive crashes without duplicating an earlier refund."""

import json
from contextlib import closing

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count
from lab8.shapes import SHAPES


@pytest.mark.student
@pytest.mark.parametrize("shape", ["workflow", "single", "orchestrator"])
@pytest.mark.parametrize(
    "crash_at",
    ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"],
)
def test_topup_crash_and_repeated_retries_keep_one_refund(public_db, shape, crash_at):
    # C-014 quotes 150,000 VND; O-515 already has a 30,000 VND refund.
    run_claim = SHAPES[shape]
    with pytest.raises(InjectedCrash, match=crash_at):
        run_claim("C-014", seed=11, store_path=str(public_db), crash_at=crash_at)

    # Inspect persisted state through a new connection, as after a restart.
    effect_committed = crash_at != "before_effect"
    with closing(connect(public_db)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM refund_ledger WHERE claim_id = ?", ("C-014",)
        ).fetchone()[0]
        assert count == int(effect_committed)
        assert committed_audit_count(conn, "C-014") == int(effect_committed)
        total = conn.execute(
            "SELECT SUM(amount_vnd) FROM refund_ledger WHERE order_id = ?", ("O-515",)
        ).fetchone()[0]
        assert total == (150000 if effect_committed else 30000)
        checkpoint = conn.execute(
            "SELECT 1 FROM checkpoints WHERE claim_id = ? AND step = 'issue_refund'",
            ("C-014",),
        ).fetchone()
        assert (checkpoint is not None) == (crash_at == "after_checkpoint")

    # Changing the model seed must not change the committed effect on retry.
    for seed in (11, 22, 55):
        result = run_claim("C-014", seed=seed, store_path=str(public_db))
        assert result.status == "resolved"
        assert result.proposal_amount == 150000
        assert len(result.refund_effects) == 1
        assert result.refund_effects[0]["amount_vnd"] == 120000
        assert result.committed_audit_count == 1

        with closing(connect(public_db)) as conn:
            refunds = conn.execute(
                "SELECT claim_id, amount_vnd FROM refund_ledger WHERE order_id = ?",
                ("O-515",),
            ).fetchall()
            assert len(refunds) == 2  # Historical refund plus this claim's top-up.
            assert sum(row["amount_vnd"] for row in refunds) == 150000
            assert sum(row["claim_id"] == "C-014" for row in refunds) == 1
            assert committed_audit_count(conn, "C-014") == 1
            checkpoint = conn.execute(
                "SELECT result_json FROM checkpoints "
                "WHERE claim_id = ? AND step = 'issue_refund'",
                ("C-014",),
            ).fetchone()
            assert checkpoint is not None
            assert json.loads(checkpoint["result_json"])["amount_vnd"] == 120000
