"""Ensure peer ablation changes accounting without changing refund decisions."""

import json
from pathlib import Path

import pytest

from bonus.swarm_no_peer import run_claim
from lab8.app import prepare_store
from lab8.durability import InjectedCrash
from lab8.metrics import check_trace
from lab8.shapes import swarm_reference

pytestmark = pytest.mark.student


@pytest.mark.parametrize("seed", [11, 55])
def test_peer_ablation_keeps_decision_and_separate_trace(tmp_path, seed):
    baseline_db = tmp_path / "baseline.sqlite"
    variant_db = tmp_path / "variant.sqlite"
    prepare_store(baseline_db)
    prepare_store(variant_db)
    baseline = swarm_reference.run_claim("C-002", seed=seed, store_path=str(baseline_db))
    variant = run_claim("C-002", seed=seed, store_path=str(variant_db))

    for field in ("status", "proposal_amount", "refund_effects", "committed_audit_count", "tool_calls"):
        assert getattr(variant, field) == getattr(baseline, field)
    assert variant.model_calls == baseline.model_calls - 1
    assert variant.cost_estimate < baseline.cost_estimate
    assert variant.shape == "swarm_no_peer"
    assert variant.run_id != baseline.run_id
    assert variant.trace_path != baseline.trace_path
    assert check_trace(variant.as_dict()) == (True, "ok")
    baseline_trace = json.loads(Path(baseline.trace_path).read_text(encoding="utf-8"))
    variant_trace = json.loads(Path(variant.trace_path).read_text(encoding="utf-8"))
    assert variant_trace["events"] == baseline_trace["events"]


@pytest.mark.parametrize(
    "crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"]
)
def test_peer_ablation_restores_reference_after_crash(public_db, crash_at):
    original_complete = swarm_reference.complete
    original_run_id = swarm_reference.make_run_id
    with pytest.raises(InjectedCrash, match=crash_at):
        run_claim("C-001", seed=11, store_path=str(public_db), crash_at=crash_at)
    assert swarm_reference.complete is original_complete
    assert swarm_reference.make_run_id is original_run_id
    resumed = swarm_reference.run_claim("C-001", seed=11, store_path=str(public_db))
    assert resumed.shape == "swarm"
    assert resumed.model_calls == 3
    assert resumed.status == "resolved"
    assert resumed.committed_audit_count == 1
