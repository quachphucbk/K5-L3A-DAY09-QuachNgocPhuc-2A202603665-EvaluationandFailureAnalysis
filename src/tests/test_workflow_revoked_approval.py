"""Workflow must honor the claim's selected approval and preserve denial audit."""

import json
from contextlib import closing

import pytest

from lab8.db import connect
from lab8.shapes.workflow import run_claim


@pytest.mark.student
def test_workflow_revoked_approval_is_not_rescued_by_spare(public_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with closing(connect(public_db)) as conn:
        conn.execute(
            "UPDATE approvals SET status = 'revoked' "
            "WHERE approval_id = (SELECT approval_id FROM claims WHERE claim_id = ?)",
            ("C-001",),
        )
        conn.execute(
            "INSERT INTO approvals "
            "(approval_id, claim_id, approved_vnd, status, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("A-WORKFLOW-SPARE", "C-001", 35000, "valid", "2027-12-31"),
        )
        conn.commit()

    # Retrying must neither pay nor duplicate the same policy denial.
    for seed in (11, 55):
        result = run_claim("C-001", seed=seed, store_path=str(public_db))
        assert result.status == "denied"
        assert result.proposal_amount == 35000
        assert result.error_reason == "approval_revoked"
        assert result.refund_effects == []
        assert result.committed_audit_count == 0

        with closing(connect(public_db)) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM refund_ledger WHERE order_id = ?", ("O-107",)
            ).fetchone()[0] == 0
            events = conn.execute(
                "SELECT event_type, details_json FROM audit_events WHERE claim_id = ?",
                ("C-001",),
            ).fetchall()
            assert len(events) == 1
            assert events[0]["event_type"] == "policy_denied"
            assert json.loads(events[0]["details_json"])["reason"] == "approval_revoked"
