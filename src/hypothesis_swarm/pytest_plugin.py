"""Pytest plugin — appends the swarm footer to Hypothesis failure reports.

Auto-registered via the [project.entry-points.pytest11] table in
pyproject.toml. Users get the footer with no wiring.
"""

from __future__ import annotations


def pytest_configure(config) -> None:  # noqa: ARG001
    # TODO: hook Hypothesis's failure-reporting machinery to emit:
    #   Swarm signature (pinned):  {...}   disabled: {...}
    #   Swarm signature (drift):   {...}   disabled: {...}
    #   Verdict: <essential | discovery-only | uniform-also-finds>
    #
    # Likely hook: register a hypothesis.event listener or wrap the
    # falsifying-example printer. Exact API depends on Hypothesis
    # version.
    pass
