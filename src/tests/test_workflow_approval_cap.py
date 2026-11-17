"""Workflow must preserve the full quote when approval caps the refund."""

from contextlib import closing

import pytest

from lab8.db import connect
from lab8.durability import committed_audit_count
from lab8.shapes.workflow import run_claim


@pytest.mark.student
def test_workflow_capped_approval_preserves_quote_on_retry(public_db, tmp_path, monkeypatch):
    # Keep generated traces isolated from the repository.
    monkeypatch.chdir(tmp_path)
    with closing(connect(public_db)) as conn:
        # C-001 qualifies for a 35,000 VND shipping refund.
        conn.execute(
            "UPDATE approvals SET approved_vnd = ? "
            "WHERE approval_id = (SELECT approval_id FROM claims WHERE claim_id = ?)",
            (20000, "C-001"),
        )
        conn.commit()

    # A different seed on replay must not change or duplicate the payment.
    for seed in (11, 55):
        result = run_claim("C-001", seed=seed, store_path=str(public_db))
        assert result.status == "resolved"
        assert result.proposal_amount == 35000
        assert len(result.refund_effects) == 1
        assert result.refund_effects[0]["amount_vnd"] == 20000
        assert result.committed_audit_count == 1

        # Verify persisted state independently of the returned result.
        with closing(connect(public_db)) as conn:
            refunds = conn.execute(
                "SELECT amount_vnd FROM refund_ledger WHERE order_id = ?",
                ("O-107",),
            ).fetchall()
            assert len(refunds) == 1
            assert refunds[0]["amount_vnd"] == 20000
            assert committed_audit_count(conn, "C-001") == 1
