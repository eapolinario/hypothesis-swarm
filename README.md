# hypothesis-swarm

> Randomly disables a subset of your `@rule`s per test case — finds bugs
> caused by the *absence* of operations that uniform random testing misses.

**Status:** pre-alpha. The API is sketched; the implementation is a skeleton.

## What it does

Classical property-based testing draws every API call from the same
distribution on every test case. Some bugs only surface when certain
operations *never happen* — a stack overflows only if `clear` is never
called, a cache thrashes only if `get` never fires between `put`s.
Uniform random testing eventually finds these but pays for it in test
budget.

**Swarm testing** (Groce et al., ISSTA 2012) instead picks a random
*subset* of operations per test case and only fires those. This package
brings swarm testing to [Hypothesis](https://hypothesis.readthedocs.io/).

## Usage

Drop-in for `RuleBasedStateMachine`:

```python
from hypothesis import strategies as st
from hypothesis_swarm import SwarmStateMachine, rule, invariant

class BoundedStack(SwarmStateMachine):
    MAX = 8

    def __init__(self):
        super().__init__()
        self.stack = []

    @rule(x=st.integers())
    def push(self, x):
        self.stack.append(x)         # BUG: no bounds check

    @rule()
    def pop(self):
        if self.stack:
            self.stack.pop()

    @rule()
    def clear(self):
        self.stack.clear()

    @invariant()
    def not_overflowed(self):
        assert len(self.stack) <= self.MAX

TestBoundedStack = BoundedStack.TestCase
```

Each `@rule`-decorated method is automatically a *feature*. Per test
case, a non-empty subset is enabled; rules outside the subset never
fire. When the test fails, the report tells you which subset triggered
the bug — and whether the swarm restriction was actually load-bearing.

For stateless generators, use the `swarm()` combinator:

```python
from hypothesis import given, strategies as st
from hypothesis_swarm import swarm

expression = swarm({
    "lit": st.integers(),
    "add": st.tuples(st.deferred(lambda: expression),
                     st.deferred(lambda: expression)),
    "mul": st.tuples(st.deferred(lambda: expression),
                     st.deferred(lambda: expression)),
    "neg": st.deferred(lambda: expression),
})

@given(expression)
def test_eval_matches_reference(expr): ...
```

See the design document at [`docs/design.md`](docs/design.md) for the
full API surface, the two-phase shrinker design, and the validation
plan.

## Development

```sh
nix develop     # or: direnv allow
uv sync         # install dependencies into .venv
just test
```

Recipes: `just build`, `just test`, `just fmt`, `just lint`, `just clean`.

## References

- Groce, A., Zhang, C., Eide, E., Chen, Y., & Regehr, J. (2012).
  *Swarm Testing.* ISSTA 2012.

## License

MIT.
