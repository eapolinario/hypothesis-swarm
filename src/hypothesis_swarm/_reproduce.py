"""@reproduce_failure_swarm — wraps Hypothesis's reproducer.

Restores both the choice sequence (via Hypothesis's @reproduce_failure)
and the swarm signature (which would otherwise be re-sampled from the
side RNG).
"""

from __future__ import annotations

from typing import Callable, Iterable

from hypothesis import reproduce_failure


def reproduce_failure_swarm(
    *,
    hypothesis_version: str,
    signature: Iterable[str],
    blob: bytes,
) -> Callable:
    """Decorator: pin the swarm signature and replay a Hypothesis blob.

    TODO: needs to install the signature into the side RNG path before
    the test runs, then delegate the actual replay to Hypothesis's
    @reproduce_failure.
    """
    sig = frozenset(signature)

    def decorate(fn: Callable) -> Callable:
        # Install the signature override on the test function for
        # SwarmStateMachine.__init__ to pick up.
        setattr(fn, "_hypothesis_swarm_pinned_signature", sig)
        return reproduce_failure(hypothesis_version, blob)(fn)

    return decorate
