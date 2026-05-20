"""Extended @rule decorator.

Wraps hypothesis.stateful.rule with two extra kwargs:

    swarm_tag: str | None   Group rules under one feature tag. Default
                            is the wrapped function's __name__.
    swarm:     bool         If False, this rule is always enabled and
                            never appears in the swarm signature.

The underlying hypothesis.stateful.rule is called with the swarm-specific
kwargs stripped; metadata is attached to the resulting wrapper as
attributes consumed by SwarmStateMachine.
"""

from __future__ import annotations

from typing import Any, Callable

from hypothesis.stateful import rule as _hypothesis_rule

_SWARM_TAG_ATTR = "_hypothesis_swarm_tag"
_SWARM_ENABLED_ATTR = "_hypothesis_swarm_eligible"


def rule(*, swarm_tag: str | None = None, swarm: bool = True, **kwargs: Any) -> Callable:
    """Drop-in for hypothesis.stateful.rule with swarm metadata."""
    inner = _hypothesis_rule(**kwargs)

    def wrap(fn: Callable) -> Callable:
        wrapped = inner(fn)
        tag = swarm_tag if swarm_tag is not None else fn.__name__
        setattr(wrapped, _SWARM_TAG_ATTR, tag)
        setattr(wrapped, _SWARM_ENABLED_ATTR, swarm)
        return wrapped

    return wrap
