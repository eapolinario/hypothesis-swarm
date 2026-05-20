"""swarm() — stateless strategy combinator.

Per test case, samples a non-empty subset of tags via a side RNG and
returns one_of restricted to that subset. Recursive references via
st.deferred work because the active subset is fixed for the whole
test case.
"""

from __future__ import annotations

import os
import random
from typing import Mapping

from hypothesis import strategies as st


def swarm(
    mapping: Mapping[str, st.SearchStrategy],
    *,
    min_features: int = 1,
    distribution: str = "bernoulli",
) -> st.SearchStrategy:
    """Return a strategy that per-case restricts to a random subset of mapping.

    Args:
        mapping:       Tag -> sub-strategy. Tags are arbitrary strings.
        min_features:  Never sample a subset smaller than this.
        distribution:  "bernoulli" | "fixed_k" | "size_biased".
    """
    if not mapping:
        raise ValueError("swarm() requires at least one tagged sub-strategy")
    tags = list(mapping.keys())

    def _sample_subset() -> list[str]:
        rng = random.Random(os.urandom(16))  # TODO: side RNG, see _stateful
        for _ in range(64):
            if distribution == "bernoulli":
                chosen = [t for t in tags if rng.random() < 0.5]
            elif distribution == "fixed_k":
                k = max(min_features, len(tags) // 2)
                chosen = rng.sample(tags, k)
            elif distribution == "size_biased":
                k = int(rng.triangular(min_features, len(tags), len(tags)))
                chosen = rng.sample(tags, k)
            else:
                raise ValueError(f"unknown distribution: {distribution!r}")
            if len(chosen) >= min_features:
                return chosen
        return tags

    @st.composite
    def _swarm_strategy(draw):
        active = _sample_subset()
        return draw(st.one_of(*(mapping[t] for t in active)))

    return _swarm_strategy()
