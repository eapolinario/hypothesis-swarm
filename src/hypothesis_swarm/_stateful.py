"""SwarmStateMachine — RuleBasedStateMachine with per-case rule subsetting.

The swarm signature is sampled out-of-band (a side RNG seeded from the
Hypothesis per-case entropy), not from the choice sequence. This makes
Phase A (pinned shrink) free: Hypothesis's shrinker cannot touch
self._swarm_enabled because no draw produced it.

Phase B (drift) is implemented in _shrink.py as a Python-level outer
loop over signatures, re-running Phase A under progressively smaller
subsets.
"""

from __future__ import annotations

import random
from typing import ClassVar

from hypothesis.stateful import RuleBasedStateMachine

from hypothesis_swarm._rule import _SWARM_ENABLED_ATTR, _SWARM_TAG_ATTR


class SwarmStateMachine(RuleBasedStateMachine):
    """Drop-in replacement for RuleBasedStateMachine with swarm testing.

    Class-level knobs:
        swarm_min_features:   int   Never sample fewer than N features.
        swarm_distribution:   str   "bernoulli" | "fixed_k" | "size_biased"
        swarm_drift:          bool  Run Phase B drift shrink after pin.
    """

    swarm_min_features: ClassVar[int] = 1
    swarm_distribution: ClassVar[str] = "bernoulli"
    swarm_drift: ClassVar[bool] = True

    def __init__(self) -> None:
        super().__init__()
        self._swarm_enabled: frozenset[str] = self._sample_swarm_signature()

    # ------------------------------------------------------------------ #
    # Swarm signature sampling
    # ------------------------------------------------------------------ #

    @classmethod
    def _all_swarm_tags(cls) -> list[str]:
        tags: list[str] = []
        seen: set[str] = set()
        for name in dir(cls):
            attr = getattr(cls, name, None)
            if attr is None:
                continue
            if not getattr(attr, _SWARM_ENABLED_ATTR, False):
                continue
            tag = getattr(attr, _SWARM_TAG_ATTR, None)
            if tag is None or tag in seen:
                continue
            seen.add(tag)
            tags.append(tag)
        return tags

    @classmethod
    def _always_on_tags(cls) -> set[str]:
        always: set[str] = set()
        for name in dir(cls):
            attr = getattr(cls, name, None)
            if attr is None:
                continue
            if hasattr(attr, _SWARM_TAG_ATTR) and not getattr(attr, _SWARM_ENABLED_ATTR, True):
                tag = getattr(attr, _SWARM_TAG_ATTR)
                always.add(tag)
        return always

    def _sample_swarm_signature(self) -> frozenset[str]:
        rng = self._make_side_rng()
        tags = type(self)._all_swarm_tags()
        always = type(self)._always_on_tags()
        if not tags:
            return frozenset(always)

        dist = type(self).swarm_distribution
        min_features = type(self).swarm_min_features

        for _ in range(64):  # reject-and-retry until we hit min_features
            if dist == "bernoulli":
                chosen = {t for t in tags if rng.random() < 0.5}
            elif dist == "fixed_k":
                k = max(min_features, len(tags) // 2)
                chosen = set(rng.sample(tags, k))
            elif dist == "size_biased":
                # Pick subset size from a triangular distribution biased
                # toward larger subsets, then sample without replacement.
                k = int(rng.triangular(min_features, len(tags), len(tags)))
                chosen = set(rng.sample(tags, k))
            else:
                raise ValueError(f"unknown swarm_distribution: {dist!r}")
            if len(chosen) >= min_features:
                return frozenset(chosen | always)
        # Fallback: enable everything.
        return frozenset(tags) | frozenset(always)

    def _make_side_rng(self) -> random.Random:
        """Per-test-case RNG, derived from Hypothesis's per-case entropy.

        TODO: replace os.urandom() with a draw from Hypothesis's
        per-case random source so reproducers work end-to-end. The
        out-of-band requirement is that this RNG must not consume bytes
        from the choice sequence.
        """
        import os
        return random.Random(os.urandom(16))

    # ------------------------------------------------------------------ #
    # Rule scheduling
    # ------------------------------------------------------------------ #

    # TODO: override RuleBasedStateMachine's rule-selection internals so
    # that disabled rules are filtered out of the candidate pool before
    # Hypothesis draws which rule to fire next. The exact hook point
    # depends on Hypothesis version (rules() / _rules_strategy / etc.)
    # and is the load-bearing implementation work for v0.1.
