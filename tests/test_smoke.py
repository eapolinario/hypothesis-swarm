"""Smoke tests — verify the public API surface imports and instantiates."""

from __future__ import annotations

from hypothesis import strategies as st

from hypothesis_swarm import SwarmStateMachine, invariant, rule, swarm


def test_version_exposed():
    import hypothesis_swarm

    assert hypothesis_swarm.__version__


def test_swarm_combinator_returns_strategy():
    s = swarm({"a": st.integers(), "b": st.text()})
    assert hasattr(s, "example")


def test_state_machine_subclass_has_swarm_enabled():
    class M(SwarmStateMachine):
        @rule(x=st.integers())
        def push(self, x): ...

        @rule()
        def pop(self): ...

        @rule(swarm=False)
        def setup(self): ...

        @invariant()
        def always(self): ...

    tags = M._all_swarm_tags()
    assert "push" in tags
    assert "pop" in tags
    assert "setup" not in tags  # swarm=False excluded
