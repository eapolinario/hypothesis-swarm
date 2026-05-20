"""hypothesis-swarm — swarm testing for Hypothesis.

Public API:
    SwarmStateMachine       Base class. Drop-in for RuleBasedStateMachine.
    rule                    Re-exported from hypothesis.stateful (extended
                            kwargs: swarm_tag, swarm).
    invariant               Re-exported from hypothesis.stateful.
    swarm                   Strategy combinator for stateless generators.
    reproduce_failure_swarm Decorator wrapping @reproduce_failure to also
                            restore the swarm signature.
"""

from hypothesis.stateful import invariant

from hypothesis_swarm._rule import rule
from hypothesis_swarm._stateful import SwarmStateMachine
from hypothesis_swarm._stateless import swarm
from hypothesis_swarm._reproduce import reproduce_failure_swarm

__version__ = "0.1.0"

__all__ = [
    "SwarmStateMachine",
    "rule",
    "invariant",
    "swarm",
    "reproduce_failure_swarm",
    "__version__",
]
