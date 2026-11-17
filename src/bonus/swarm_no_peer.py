"""Research ablation: omit the unused peer acknowledgement, keeping swarm logic.

Run only in the sequential benchmark process. Scoped patches restore the official
swarm after each call, including when an InjectedCrash propagates. The separate
shape/run ID prevents the variant from overwriting the baseline's trace.
"""

from dataclasses import replace
from unittest.mock import patch

from lab8.mock_llm import complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes import swarm_reference

SHAPE = "swarm_no_peer"


def _complete_without_peer(budget: Budget, *, seed: int, purpose: str, prompt: str) -> str:
    if purpose == "peer":
        return ""  # The reference never uses this acknowledgement's contents.
    return complete(budget, seed=seed, purpose=purpose, prompt=prompt)


def run_claim(
    claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None
) -> RunResult:
    def variant_run_id(_shape: str, claim_id: str, seed: int) -> str:
        return make_run_id(SHAPE, claim_id, seed)

    with patch.object(swarm_reference, "complete", _complete_without_peer), patch.object(
        swarm_reference, "make_run_id", variant_run_id
    ):
        result = swarm_reference.run_claim(
            claim_id, seed=seed, store_path=store_path, crash_at=crash_at
        )
    return replace(result, shape=SHAPE)
