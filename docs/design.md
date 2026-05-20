# Ideas sketch

This document is a repository of sketches. Only spur-of-the-moment kind of descriptions

## `agent://` URL scheme for NixOS

> **⚠️ DEPRECATED — moved to implementation.**
> This sketch is now being implemented in [https://github.com/eapolinario/sigil](https://github.com/eapolinario/sigil).
> Kept here for historical context; do not edit further.

Experiment with registering an `agent` URL scheme on NixOS. Unclear yet what
happens when such a URL is embedded in a document and activated, but the core
intent is: clicking/opening an `agent://` URL triggers a stateless invocation
of `copilot` scoped to a specific project, where the project is encoded as
part of the URL.

### URL grammar (proposed)

```
agent://<project>[/<path>][?prompt=<text>&model=<id>&effort=<level>&ref=<git-ref>]
```

- `<project>` — a stable identifier, not a filesystem path. Resolved by the
  handler to a working directory (e.g. `gh:owner/repo`, `local:ideas`,
  `flake:github:owner/repo#dev`). Anything filesystem-shaped should be
  rejected at the handler boundary.
- `<path>` — optional, narrows the agent's attention to a subdirectory or
  file within the resolved project.
- `prompt` — the actual task. URL-encoded. May be empty (drops into an
  interactive session instead of `-p`).
- `model`, `effort` — map directly to `copilot --model` / `--effort`.
- `ref` — optional git ref to check out before running.

### NixOS registration mechanism

Two pieces, both expressible as a NixOS module:

1. A `.desktop` file with `MimeType=x-scheme-handler/agent;` installed into
   the system profile (`environment.systemPackages` + `xdg.mime`), so
   `xdg-open agent://...` routes to our handler. Browsers, Emacs
   `browse-url`, and most document viewers already honor this.
2. A handler binary (small Nix-built script — bash or a `writeShellApplication`
   wrapping a Python parser) on `PATH`, registered as the
   `x-scheme-handler/agent` default via `xdg.mime.defaultApplications`.

### Handler behavior

Stateless by design — no session resumption, no `--continue`, no shared
context across invocations:

1. Parse and validate the URL. Reject anything ambiguous.
2. Resolve `<project>` to a working directory. For remote projects, clone
   into a deterministic cache path (`$XDG_CACHE_HOME/agent-url/<hash>`),
   reusing if present, refreshing if `ref` is set.
3. Open a fresh terminal (Ghostty via Hyprland on this box) and `exec`:
   ```
   copilot -C <workdir> [--model <model>] [--effort <effort>] \
           [-p <prompt> --allow-all-tools | <interactive>]
   ```
4. Exit when `copilot` exits. No daemon, no background state.

### Open questions

- **Security.** This is the load-bearing question. A clickable URL that
  spawns an AI agent with shell access in *some* project is a phishing
  primitive. Mitigations to explore:
  - Mandatory confirmation dialog (`zenity`/`rofi`) showing the resolved
    project, prompt, and model before any process starts.
  - Allowlist of projects in `~/.config/agent-url/allowlist.toml`; unknown
    projects require explicit one-shot approval.
  - Never pass `--allow-all-tools` for prompts originating from untrusted
    surfaces (browsers, mail clients). Possibly key this off the calling
    `.desktop` entry.
- **Document activation semantics.** What actually happens when an
  `agent://` URL sits in a Markdown file rendered by, say, Obsidian or
  GitHub? Most renderers will refuse to linkify unknown schemes. Need to
  test: Emacs `org-mode`, Ghostty's OSC 8 hyperlinks, Firefox, Slack.
- **Project resolution registry.** Where does `gh:owner/repo` map to on
  disk? A simple convention (`~/repos/<repo>`) covers the local case;
  remote needs a cache + lock to handle concurrent clicks.
- **Interactive vs. non-interactive.** Empty `prompt=` → spawn terminal
  with interactive copilot. Non-empty → run headless and surface output
  in a notification? Or always pop a terminal?

### Use cases worth sketching

- Issue trackers: "Reproduce this bug" buttons that open in the right repo.
- Internal docs: runbook steps as one-click agent invocations.
- READMEs: "Try this locally" links that resolve to `local:<repo>` after
  the user has cloned.
- Cross-machine handoff: copy an `agent://` URL into chat, recipient opens
  it on their own box with their own credentials.

## Property-based testing framework with Swarm Testing

A property-based testing framework (à la QuickCheck/Hypothesis/proptest)
whose generator strategy implements **Swarm Testing** (Groce et al., ISSTA
2012) as a first-class feature, not a bolt-on.

### The core observation

Classical random testing draws every "feature" (API call, token, opcode,
constructor) from the *same* distribution on every test. Swarm testing
instead: for each test case, randomly pick a **subset** of features to
enable, and draw only from that subset. Empirically this dramatically
increases bug-finding power on stateful/API-heavy targets — the original
paper found ~moves the needle on real compiler bugs that uniform random
testing misses, because pathological interactions often require the
*absence* of certain operations (e.g. no `pop` calls, so the stack grows
unboundedly).

Most mainstream PBT libraries don't expose this. You can hack it by hand
(write N generators, pick one), but there's no library affordance for:
- declaring the "feature set" of a generator,
- per-test-case feature subsetting,
- shrinking that respects the swarm (don't shrink *into* a disabled
  feature, or do, and report it),
- reporting which feature subset triggered a failure.

### What the framework would provide

1. **Feature-tagged generators.** A `swarm(...)` strategy combinator for
   stateless generators, and a `SwarmStateMachine` base class where each
   `@rule`-decorated method is automatically a feature. See dedicated API
   section below.
2. **Configurable subset distribution.** Default to the paper's
   independent-Bernoulli(0.5) per feature, but allow weighted / size-biased
   / fixed-k variants.
3. **Shrinking that understands swarms.** Two-phase shrink (pin, then
   drift) that produces both the within-swarm minimal repro and the
   globally minimal one, and diffs them. See dedicated section below.
4. **Coverage feedback loop (stretch).** Combine with branch/line coverage
   (à la AFL-style PBT, e.g. `propfuzz`, `fuzzcheck`) to *learn* which
   feature subsets are productive and bias toward them. The paper itself
   is uniform; coverage-guided swarm is the obvious next step.
5. **Failure reporting.** Surface the *swarm signature* (which features
   were enabled) alongside the minimised counterexample. This is the
   actionable artifact — "this bug requires push+peek but no pop".

### Target ecosystem — decision: **Hypothesis (Python), shipped as `hypothesis-swarm`**

Locked in. Reasoning below; the other two stay on the page as honest
comparisons, not as live options.

**Why Hypothesis wins**

1. **Conceptual fit is a one-liner.** `RuleBasedStateMachine`'s
   `@rule`-decorated methods are already a tagged feature set in all but
   name. Swarm = "per test case, randomly disable a subset of `@rule`s".
   No new mental model required for existing users — it's a flag on the
   state machine. Stateless generators get a separate `swarm(...)`
   strategy combinator, but the headline product is stateful.
2. **Audience fit.** The original Groce et al. result was about
   API-sequence testing of stateful systems (compilers, file systems).
   `RuleBasedStateMachine` users are *exactly* that audience, already
   reaching for the right tool and discovering the uniform-distribution
   ceiling on their own.
3. **Distribution is solved.** `pip install hypothesis-swarm`. No
   ecosystem to bootstrap, no "first you need to learn Rust" tax. The
   whole pitch is closing the gap between research idea and
   `pip install`-able artifact — picking a language without `pip` would
   contradict the pitch.
4. **The shrinker is hard, but hard in the *useful* direction.**
   Hypothesis has the most sophisticated shrinker in PBT (choice-sequence
   based, internal-representation aware). Making swarm play nicely with
   it is real work, but the ceiling is much higher than reimplementing a
   weaker shrinker from scratch. See the dedicated shrinker section
   below — this is the load-bearing technical question.

**Why not proptest (Rust)**

Serious second choice. The stateful PBT story in Rust is genuinely
underbaked (`proptest-state-machine` exists but is thin), so there's a
bigger raw *gap* to fill. But: smaller audience, the upstream stateful
API is still moving, and proptest's shrinker is weaker so we'd get less
leverage from the host framework. A `proptest-swarm` crate is a credible
v2 once the Hypothesis version has validated the design — not the
opening move.

**Why not greenfield**

The pitch is "13-year-old technique, no mainstream `pip install`-able
implementation." Greenfield re-creates that exact gap. Building a PBT
framework from scratch is a multi-year project just to reach
shrinking parity with Hypothesis, before swarm enters the picture. Zero
distribution, zero leverage, infinite yak-shaving. This is the obvious
trap.

**Risks of going Hypothesis-first**

- **Upstream opinions.** Hypothesis's maintainers have strong views on
  what does and doesn't belong in the core library, and have historically
  de-emphasised "uniform random" framings in favour of targeted /
  coverage-guided search. Mitigation: ship as an *external* package, not
  a PR. Use Hypothesis's public extension points (custom strategies,
  `RuleBasedStateMachine` subclass) and don't ask permission. If it gets
  traction, *then* propose upstream integration from a position of
  evidence.
- **Shrinker entanglement.** The choice-sequence shrinker doesn't know
  about swarm signatures and will happily shrink across them. This is
  the dedicated next-iteration topic; the answer determines whether the
  whole design holds together.
- **Performance ceiling.** Python is slow. For the most dramatic
  swarm-testing wins (large compiler / VM fuzzing), users may eventually
  want the proptest version. Acceptable — v1 audience is Python-library
  authors testing Python state machines, where Python speed is fine.

### Shrinker design — decision: **two-phase shrink (pin, then drift), with the swarm signature stored out-of-band**

This is the load-bearing technical question. The answer determines both
the implementation strategy and the failure-report UX.

#### Background: how Hypothesis shrinks

Hypothesis's shrinker operates on the *choice sequence* — the linear log
of every random decision the strategy made (which branch of a `one_of`,
which integer, how long a list, which rule to fire next). Shrinking is:
find a shortlex-smaller choice sequence that still triggers the failure.
Passes include deletion of chunks, zeroing of integers, block swaps, and
structured reductions. The shrinker is semantics-agnostic; it doesn't
know which bytes mean what.

The critical property: when a shrunk choice sequence is replayed, the
*rest* of the sequence is reinterpreted under the new prefix. If an
earlier decision changes, downstream `draw()`s may consume different
bytes and produce different values — the test case morphs as a whole.

#### The two modes

**Pin-the-swarm-signature.** During shrinking, freeze the swarm subset
selection. The shrinker only reduces the rule firings, their arguments,
and the sequence length — never the swarm signature itself. Output: the
smallest test case that triggers the bug *under exactly the original
set of enabled features*. This is the artifact that justifies swarm's
existence: "this bug requires push+peek with no pop, here is the
minimal trace under that restriction".

**Let-it-drift.** Allow the shrinker to also reduce the swarm signature
(toggle features on/off) as part of its passes. Output: the globally
smallest reproducer, regardless of which features were originally
enabled. May reveal that the bug doesn't actually require the swarm
restriction at all — a useful negative result — or may find a *different*
feature subset that still triggers a smaller failure.

Neither subsumes the other. Pinned answers "what is this swarm bug?".
Drift answers "what is the smallest repro, and was swarm even
load-bearing?". A user investigating a failure wants both.

#### Decision: do both, in sequence, and diff the result

1. **Phase A — pinned shrink.** Run Hypothesis's full shrinker passes
   with the swarm signature held constant. Produce the within-swarm
   minimal counterexample. This is the *primary* artifact.
2. **Phase B — drift shrink.** Starting from Phase A's output, unfreeze
   the swarm signature and run shrinking again. If the result is
   strictly smaller (by Hypothesis's shortlex order) or uses a strictly
   smaller feature subset, report it as a *secondary* artifact.
3. **Diff the signatures.** The failure report shows:
   - Pinned repro: features `{push, peek}`, trace length 4.
   - Drift repro: features `{push}` only, trace length 3.
   - Verdict: "swarm restriction was load-bearing for discovery but not
     for the minimal repro" / "swarm restriction is essential; drift
     could not reduce features further" / "bug exists under uniform
     random; swarm just found it faster".

The verdict line is the actually-useful thing. It tells the user
whether to file the bug as "crashes when feature X is absent" or just
"crashes, here is a trace".

#### Implementation: store the swarm signature *out of band*

The naive approach — draw the swarm signature as the first N bits of
the choice sequence — makes pinning hard. Hypothesis's shrinker doesn't
expose a clean public API for "freeze bytes 0..N of the choice
sequence"; the internal `ConjectureData` has the concept but using it
from an extension means binding to private internals that drift across
releases.

Cleaner approach: the swarm signature does not live in the choice
sequence at all. Instead, `SwarmStateMachine` (a `RuleBasedStateMachine`
subclass) holds the signature as an *instance attribute* sampled in
`__init__` via a separate RNG seeded from the Hypothesis test seed.
Rule selection within the state machine reads `self._swarm_enabled`
and filters the candidate rule list accordingly — the choice sequence
only records *which of the enabled rules* fires.

Consequences:
- **Phase A (pinned) comes for free.** Hypothesis shrinks the choice
  sequence, which by construction cannot affect `self._swarm_enabled`.
  No internal API needed.
- **Phase B (drift) is implemented as a custom shrinker pass.** After
  Hypothesis declares Phase A converged, the extension iterates over
  swarm signatures (greedy: try removing each enabled feature; if the
  test still fails, re-run Phase A under the smaller signature) until
  no further reduction is possible. This is a Python-level loop on top
  of Hypothesis's `@example` / `find` machinery, not a shrinker-internal
  modification.
- **Reproducibility.** The full repro is `(swarm_signature,
  choice_sequence)`. Hypothesis's database already stores choice
  sequences; we side-car the signature in the same database under a
  related key. `@reproduce_failure` gets a wrapper that restores both.
- **Cost.** Phase B is O(features) extra shrinker runs in the worst
  case. For typical state machines (~10 rules), negligible. Gated by a
  `swarm_drift=True/False` setting; default on.

#### Stateless generators (`swarm(...)` combinator)

Same pattern: the strategy holds the signature as a closure-local
variable sampled once per test case from a side RNG, not from
`draw()`. Phase A / Phase B logic is identical.

#### What this rules out

- **No semantic-aware shrinker passes.** We do not attempt to teach
  Hypothesis's shrinker about swarm structure. All the cleverness lives
  in (a) the out-of-band storage trick and (b) the Phase B outer loop.
  If Hypothesis's shrinker gets smarter in the future, we inherit it
  for free.
- **No partial pinning.** The signature is either fully pinned (Phase A)
  or fully free (Phase B). "Pin half the features" is not supported and
  there's no clear use case.

### User-facing API — decision: **base-class for stateful, `swarm()` combinator for stateless, zero new annotations in the default case**

The headline goal: an existing `RuleBasedStateMachine` user adopts swarm
by changing *one import and one base class*. No per-rule annotations, no
config file, no test-runner changes. Everything else is a knob with a
sensible default.

#### Stateful: `SwarmStateMachine`

The canonical pedagogical case — a bounded stack with a swarm-discoverable
bug (overflow only triggers when `clear` is never called):

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

Three rules → three swarm features (`push`, `pop`, `clear`). Per test
case, `SwarmStateMachine.__init__` samples a non-empty subset via a side
RNG (seeded from Hypothesis's per-case entropy, not from the choice
sequence — see shrinker section). Rule scheduling filters against the
enabled set.

Uniform random eventually triggers the overflow but takes many cases;
swarm hits it almost immediately on any case where `clear` is disabled
and `push` is enabled. The pinned shrink reports: "features `{push,
not pop}`" (or similar) — the absence is the load-bearing signal.

#### Per-rule controls (when defaults aren't enough)

```python
class FileSystem(SwarmStateMachine):
    # Group related rules under one tag — enabling/disabling moves them
    # together.
    @rule(path=paths(), swarm_tag="writes")
    def create(self, path): ...

    @rule(path=paths(), swarm_tag="writes")
    def write(self, path): ...

    @rule(path=paths(), swarm_tag="writes")
    def delete(self, path): ...

    @rule(path=paths())  # default tag: "read"
    def read(self, path): ...

    # Setup/teardown-shaped rules that must always be available.
    @rule(swarm=False)
    def mount(self): ...
```

Resolution rules:
- Default `swarm_tag` is the method name.
- Rules with the same tag are toggled together.
- `swarm=False` means "always enabled, never part of the signature".
  Use sparingly — fixtures, mount/unmount, anything that would make
  every other rule a no-op if disabled.

Class-level knobs (on `SwarmStateMachine` subclass body):

```python
class FileSystem(SwarmStateMachine):
    swarm_min_features = 1                # never sample the empty set
    swarm_distribution = "bernoulli"      # default: indep. Bernoulli(0.5)
    #                  | "fixed_k"        # exactly k features per case
    #                  | "size_biased"    # bias toward larger subsets
    swarm_drift = True                    # Phase B on by default
    ...
```

#### Stateless: `swarm()` combinator

For grammar-based generators, token streams, or any
`one_of`-shaped strategy where the *alphabet* should vary per case:

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
def test_eval_matches_reference(expr):
    assert eval_mine(expr) == eval_reference(expr)
```

`swarm(mapping, *, min_features=1, distribution="bernoulli")` returns a
strategy that per test case samples a subset of keys (same side-RNG
mechanism as the stateful case) and draws via `one_of` restricted to
that subset. Recursive references via `st.deferred` work because the
active subset is fixed for the whole test case.

#### Failure report format

A pytest plugin (auto-registered on install) intercepts Hypothesis
failures from swarm-aware tests and appends a footer:

```
Falsifying example: BoundedStack(
    state.push(x=0)
    state.push(x=0)
    ... ×9 more
)

Swarm signature (pinned):  {push}              disabled: {pop, clear}
Swarm signature (drift):   {push}              disabled: {pop, clear}
Verdict: swarm restriction is essential — drift could not reduce
         features further. Bug is characterised by the absence of
         {pop, clear}.
```

Three verdict shapes, as decided in the shrinker section:
- "swarm restriction is essential" (drift == pinned)
- "swarm restriction was load-bearing for discovery but not for the
  minimal repro" (drift strictly smaller features-wise)
- "bug exists under uniform random; swarm just found it faster" (drift
  signature is all features)

#### Reproducers

Hypothesis's `@reproduce_failure(version, blob)` is wrapped:

```python
from hypothesis_swarm import reproduce_failure_swarm

@reproduce_failure_swarm(
    hypothesis_version="6.x",
    signature={"push"},
    blob=b"...",
)
@given(...)
def test_eval_matches_reference(expr): ...
```

Restores both the choice sequence (via Hypothesis's normal machinery)
and the swarm signature (which would otherwise be re-sampled from the
side RNG). Side-cars in Hypothesis's example database under a related
key, so `--hypothesis-seed` reproducibility is preserved.

#### What's deliberately *not* in the API

- **No `@swarm_rules` class decorator.** Base-class only. Decorators
  that need to override `__init__` get messy; the base class is the
  honest mechanism.
- **No coverage-guided swarm in v1.** That's the stretch goal from the
  top of the sketch and lives behind a separate import
  (`hypothesis_swarm.coverage`) so users opt in explicitly.
- **No per-test-case signature override.** Users cannot say "run this
  test under exactly this signature" except via `reproduce_failure_swarm`.
  Avoids people defeating the random-subsetting that makes swarm work.
- **No `swarm=True` flag on `@given`.** The `swarm()` combinator is the
  single way to opt a stateless generator in. One way to do it.

### Empirical validation — decision: **three-tier benchmark suite, pre-registered, against three different skeptics**

The one experiment that kills the project (if results come back flat) is
Tier 2 below. Build it first; the rest is supporting evidence.

#### Three skeptics, three experiments

Different audiences are convinced by different numbers. Address each
explicitly rather than producing one mushy benchmark that satisfies
nobody.

1. **The PBT user.** "I already use Hypothesis. Does this find bugs I
   don't find today, within a budget I'd actually spend?"
2. **The academic.** "The 2012 paper showed swarm wins on C compilers
   with hand-rolled testers. Does the result replicate when layered on
   top of Hypothesis's targeted/shrinking machinery?"
3. **The Hypothesis maintainer.** "Why isn't your win just better
   `target()` tuning, or smarter `Phase.generate`?"

#### Tier 1 — pedagogical / instrumentation check (smoke tests)

Known-buggy toys where swarm *must* win or the implementation is
broken. Verifies the measurement infrastructure, not the technique.

- `BoundedStack` (the API-section example) — overflow when `clear`
  disabled.
- LRU cache with seeded eviction bug — only triggers if `get` never
  fires between `put`s.
- Toy stack VM with a deliberately seeded opcode-interaction bug
  (mirrors the Groce paper's headline example, in Python).

Success criterion: swarm finds the bug in <10% of the trials stock
Hypothesis needs. If this doesn't hold, stop — the bug isn't in the
benchmark, it's in our code.

#### Tier 2 — historical replication (the load-bearing experiment)

Mine real Python projects for *historical bugs* found by Hypothesis
stateful testing. Check out the pre-fix commit, package the
`RuleBasedStateMachine` as both a stock Hypothesis test and a
`SwarmStateMachine` test (one base-class swap), and measure
time-to-first-failure on each.

Candidate projects (chosen for documented stateful-testing bug history
and an active commit log to mine):

- **`sortedcontainers`** — famously fuzzed by Hypothesis; multiple
  historical bugs in `SortedList` / `SortedDict` with known repro
  patterns.
- **`python-rope`** or **`jedi`** — refactoring tools with state
  machines over edit operations.
- **`sqlite3` (stdlib)** — wrap a state machine over connection /
  cursor / transaction ops. SQLite itself is mature, but the *binding*
  has had bugs.
- **`cachetools`** — cache eviction policies are classic
  swarm-discoverable territory.
- **`urllib.parse`** / **`yarl`** — grammar-style swarm targets.

Methodology:
- Pre-register the target list and bug list *before* running anything.
  Cherry-picking after the fact is the #1 way to make this benchmark
  worthless.
- For each historical bug: check out the parent of the fix commit,
  port the existing Hypothesis test (if any) or write a minimal one,
  then run both stock and swarm conditions with identical compute
  budgets.
- 100 trials per (bug, condition) cell, varying seed.
- Headline metric: median time-to-first-failure (TTFF), with bootstrap
  95% CIs. Heavy-tailed distributions — don't report means.

Kill criterion: if swarm doesn't reduce median TTFF by ≥2× on a
majority of Tier-2 bugs, the project's value proposition is wrong and
should be reconsidered. **This experiment runs first.**

#### Tier 3 — fresh bug-finding (the show-me-the-bodies experiment)

Run `hypothesis-swarm` against current releases of the Tier 2 projects
with a fixed budget (say, 24 CPU-hours per project) and report any
bugs found, with patches where possible. High variance — might find
nothing, might find a CVE. Either way the *attempt* is part of the
writeup; finding zero new bugs in mature libraries is itself a useful
result.

#### Comparison conditions (mandatory in every experiment)

- **`stock`** — vanilla Hypothesis, default settings.
- **`stock+target`** — vanilla Hypothesis with `target()` calls on a
  reasonable observable (e.g., state size). Pre-empts the
  Hypothesis-maintainer skeptic. If we can't beat this, our win is
  just "targeting works" and the paper writes itself differently.
- **`swarm`** — `hypothesis-swarm` with defaults.
- **`swarm-trivial`** — `SwarmStateMachine` with every rule tagged the
  same (degenerates to uniform). Sanity check: must perform identically
  to `stock` within noise. Catches measurement bugs where our
  infrastructure favours one branch.

#### Metrics

1. **Time-to-first-failure (TTFF).** Median + p95 + success-rate within
   budget. Mann–Whitney U for significance; bootstrap CIs.
2. **Final repro size.** Trace length, feature-subset size, blob bytes.
   Validates that the two-phase shrink design produces small artifacts,
   not just finds bugs fast.
3. **Verdict accuracy.** For each "swarm restriction is essential"
   verdict, attempt manual reproduction under uniform random with 10×
   the original budget. If it reproduces, our verdict was wrong.
   Target: <5% false-essential rate.
4. **Drift utility.** Fraction of failures where Phase B (drift) found
   a strictly smaller repro than Phase A. If this is near zero, drift
   isn't pulling its weight and should be reconsidered.

#### Statistical and reproducibility hygiene

- **Pre-register hypotheses.** Before measuring: "we expect ≥5× TTFF
  reduction on Tier 1, ≥2× median on Tier 2, no significant difference
  vs. `swarm-trivial`." Commit the file. Compare against it.
- **Seed discipline.** Trial *i* uses seed *i* across all conditions, so
  conditions see the same "luck". Variance reduction is huge.
- **Compute budget per trial fixed in wall-clock-equivalent terms**
  (Hypothesis examples-tested, not seconds — seconds let CPU-speed
  differences leak in).
- **Public repo: `hypothesis-swarm-bench`.** Nix flake + `uv` lock for
  the environment, one `just bench` command, all outputs land as CSV +
  matplotlib plots committed alongside the code. Skeptics must be able
  to reproduce the headline number in one command.

#### Deliverables

- The bench repo above, as the durable artifact.
- A README with the headline plot (TTFF distributions per condition,
  per tier) and the verdict-accuracy table.
- A blog post framing the result for the PBT-user skeptic.
- If Tier 2 numbers are strong: a short paper aimed at ISSTA / ICST,
  framed as "swarm testing at the framework level" — the academic
  skeptic's currency.

#### Known risks

- **`stock+target` eats our lunch.** Possible, especially on Tier 2 bugs
  where the bug is detectable via an observable. If true, the project's
  pitch shifts from "better than stock" to "orthogonal to targeting,
  composable with it" — and we should measure `swarm+target` too.
- **Tier 2 targets resist measurement.** Historical bugs may be too
  fast or too slow to discriminate between conditions. Mitigation: pick
  bugs from the *middle* of the difficulty distribution during target
  selection, before measuring outcomes.
- **Verdict accuracy is bad.** If the verdict line in the failure
  report is wrong >5% of the time, the UX claim from the API section
  collapses. Mitigation: gate the verdict on a confidence test (only
  emit "essential" if uniform-random retries under a substantial budget
  failed to reproduce).

### Naming — decision: **keep "swarm", package as `hypothesis-swarm`, lead the README with the mechanism**

Two small calls, neither worth more thought:

- **Package name: `hypothesis-swarm`.** Inherits academic SEO from the
  technique name and discoverability from the Hypothesis namespace.
- **README tagline leads with mechanism, not lineage.** Bad: "implements
  swarm testing (Groce et al., ISSTA 2012)". Good: "randomly disables a
  subset of your `@rule`s per test case — finds bugs caused by the
  *absence* of operations that uniform random testing misses." Cite the
  paper in paragraph two, not the headline.

Rejected: coining a new term (`feature-subset PBT`,
`restricted-alphabet testing`). "Swarm" is overloaded (Docker, PSO,
robotics) but always pairs with "testing" in context, which
disambiguates. The cost of renaming — forfeiting 13 years of citation
chain and looking like a credit grab for a known technique — exceeds
the benefit of a more self-descriptive name.

### Why bother

Swarm testing is a 13-year-old technique with strong empirical backing
that essentially no mainstream PBT library implements as a first-class
feature. The gap between "known-good research idea" and "thing a working
programmer can `pip install`" is the whole opportunity.
