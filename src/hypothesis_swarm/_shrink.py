"""Phase B (drift) shrink.

Phase A (pinned) comes for free from Hypothesis's choice-sequence
shrinker, because the swarm signature is stored out-of-band on the
SwarmStateMachine instance and not drawn from the choice sequence.

Phase B is a Python-level outer loop: starting from the Phase A repro,
greedily try removing each enabled feature; if the test still fails
under the smaller signature, accept and recurse.

The output of Phase B is the (possibly smaller) signature plus a
re-run of Phase A under that signature. The two artifacts are then
diffed for the verdict line in the failure report.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SwarmRepro:
    signature: frozenset[str]
    trace: str  # placeholder — actual repro shape TBD
    blob: bytes


@dataclass(frozen=True)
class SwarmVerdict:
    pinned: SwarmRepro
    drift: SwarmRepro

    @property
    def kind(self) -> str:
        """One of: "essential", "discovery-only", "uniform-also-finds"."""
        if self.drift.signature == self.pinned.signature:
            return "essential"
        all_features = ...  # TODO: needs the full feature set from the test
        if self.drift.signature >= self.pinned.signature:
            return "uniform-also-finds"
        return "discovery-only"


def drift_shrink(pinned: SwarmRepro, retest) -> SwarmRepro:
    """Greedy feature removal starting from a pinned-shrink repro.

    Args:
        pinned: The Phase A output.
        retest: Callable (signature) -> SwarmRepro | None. Returns a
                fresh pinned-shrink repro under the given signature, or
                None if the bug doesn't reproduce there.
    """
    best = pinned
    changed = True
    while changed:
        changed = False
        for tag in sorted(best.signature):
            candidate_sig = best.signature - {tag}
            if not candidate_sig:
                continue
            attempt = retest(candidate_sig)
            if attempt is not None:
                best = attempt
                changed = True
                break
    return best
