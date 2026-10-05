# Fast Downward (release-26.6.0): build and run optimal planning with action costs

- **Source:** submodule `third_party/downward`, tag `release-26.6.0`, commit `7ea2755`.
- **Checked against:** the in-tree README.md, BUILD.md, `docs/*.md`, `build.py`, `driver/*.py` and `src/`, plus the planner binary's own `--help`.
- **Website:** https://www.fast-downward.org/latest/ was consulted only for the lmcut page. Its `/latest/` pages may describe a newer release than ours.
- **Verified by running:** everything stated as behavior was tested on 2026-10-04 with
  Python 3.12.13 (via uv), GCC 16.2.1, CMake 4.4.2 and GNU Make 4.4.1.

## TL;DR

```bash
# build (once): out-of-tree, 4 jobs
cd /home/ilyask/projects/fast-mi/third_party/downward
cmake -S src -B /home/ilyask/projects/fast-mi/build/downward/release -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build /home/ilyask/projects/fast-mi/build/downward/release -j 4

# optimal plan with action costs
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python 3.12 python \
  /home/ilyask/projects/fast-mi/third_party/downward/fast-downward.py \
  --build /home/ilyask/projects/fast-mi/build/downward/release \
  --overall-time-limit 60s --overall-memory-limit 2G \
  --plan-file /path/to/out.plan \
  domain.pddl problem.pddl --search "astar(lmcut())"
# exit 0 = optimal plan written to /path/to/out.plan
```

Two gotchas:

1. **The problem must contain `(:metric minimize (total-cost))`.** Without it the translator silently sets every action cost to 1.
2. **No conditional effects, and nothing that compiles to axioms.** That means no `forall` conditions, no disjunctive or existential *goals*, and no `:derived` predicates. lmcut rejects all of these with exit code 34. See the feature table below.

---

## 1. Build

### What was run

Run from the submodule root. CMake shells out to `git log` / `git diff-index` there to stamp the revision.

```bash
cd /home/ilyask/projects/fast-mi/third_party/downward
cmake -S /home/ilyask/projects/fast-mi/third_party/downward/src \
      -B /home/ilyask/projects/fast-mi/build/downward/release \
      -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build /home/ilyask/projects/fast-mi/build/downward/release -j 4
```

These are exactly the flags `build.py` uses for its default `release` config: `build_configs.py: release = ["-DCMAKE_BUILD_TYPE=Release"]` plus `-G "Unix Makefiles"`.

**Time:**

| Step | Duration |
| --- | --- |
| configure | about 8 s |
| compile and link | about 1123 s |
| **total** | **about 18 min 51 s** |

These are wall-clock times with `-j 4`, measured while a concurrent 8-core ScummVM build was running. Load average was 33 at the start and about 18 at the end, so the build should be much faster on an idle machine. The full log is `build/downward/build-release.log`.

**Output:**

- `build/downward/release/bin/downward`: the C++ search binary. It is 178 MB because Release keeps `-g`.
- `build/downward/release/bin/fast_downward/translate/`: a copy of the Python translator.

**Check:** `bin/downward --internal-git-revision` prints `7ea2755`, with no `-dirty` suffix.

**LP solvers:** none were configured. `cplex_DIR` and `soplex_DIR` are unset, so LP-based heuristics are unavailable. lmcut doesn't need an LP solver.

### Why out-of-tree instead of `./build.py`

`build.py` writes into the submodule: it hard-codes `<submodule>/builds/<config>/`. The submodule's `.gitignore` *does* ignore `/builds/`, as well as `__pycache__/`, `/output.sas`, `/sas_plan` and `/sas_plan.*`. So `./build.py` would not dirty the submodule, but it would put 180+ MB inside `third_party/`. The out-of-tree dir is already ignored, because `build/downward/` sits under the superproject's own `.gitignore` entry `build/`.

`build.py` also always runs `cmake --build … -j <nproc>` and forwards extra args after `--`, so `./build.py -j4` becomes `cmake --build builds/release -j 8 -- -j4`. That *should* work: with a toy Makefile, GNU make 4.4.1 honored the last `-j` (`make -j8 -j4` → `MAKEFLAGS= -j4`). `build.py` itself was not run. Calling cmake directly avoids the ambiguity.

After building and all test runs, `GIT_OPTIONAL_LOCKS=0 git -C third_party/downward status --porcelain --ignored` is empty.

### The `--build` flag (help text is misleading)

The driver's `--help` says `--build` may be "the path to a directory holding the planner binaries". The code in `driver/run_components.py` actually does `BUILDS_DIR / build / "bin"`. Tested behavior:

| `--build` value | Result |
| --- | --- |
| `--build /home/ilyask/projects/fast-mi/build/downward/release` | works |
| `--build /home/ilyask/projects/fast-mi/build/downward/release/bin` | exit 36: "Could not find build … at …/bin/bin" |
| `--build release` (relative) | resolves to `<submodule>/builds/release/bin` (from reading the code, not tested) |

## 2. Running an optimal search

**Configuration:** `astar(lmcut())`. Its current spelling and options, from `bin/downward --help lmcut` / `--help astar`:

- `lmcut(goal_zone_detection=true, border_detection=true, cache_estimates=true, …)`
- `astar(eval, lazy_evaluator=<none>, pruning=null(), cost_type=normal, bound=infinity, max_time=infinity, …)`

`cost_type=normal` means real action costs are used. lmcut is admissible but not consistent, and `astar` hard-wires node reopening: `src/search/search_algorithms/plugin_astar.cc:52` has `options_copy.set("reopen_closed", true);`, and the run log says "Conducting best first search with reopening closed nodes". So the plan is optimal.

**Alias:** `--alias seq-opt-lmcut` is defined in `driver/aliases.py` as exactly `["--search", "astar(lmcut())"]`. It was tested and gives an identical result. `--alias` cannot be combined with `--search …`.

**Command layout:** driver options come *before* the input files, and component options come *after* them.

```
fast-downward.py [driver opts] [DOMAIN] PROBLEM --search "astar(lmcut())"
```

- If DOMAIN is omitted, the driver looks for `domain.pddl` next to the problem, among a few other naming rules.
- If the single input file starts with `begin_version`, it is treated as a translated SAS file and only the search runs.

**Files written, all relative to the cwd unless overridden:**

| File | Default | Override | Notes |
| --- | --- | --- | --- |
| plan | `./sas_plan` | `--plan-file FILE` | Any existing `FILE`, `FILE.1`, `FILE.2`, … are **deleted at startup**. Anytime configs write `FILE.1`, `FILE.2`, …; `astar` writes only `FILE`. No plan file is written if no plan is found. |
| translator output | `./output.sas` | `--sas-file FILE` (implies `--keep-sas-file`) | Deleted after search by default. |

**Running concurrently:** run each job in its own fresh temp dir as cwd, or pass both `--plan-file` and `--sas-file`. Otherwise concurrent runs clobber each other's `output.sas` / `sas_plan`.

**Keeping the submodule clean:** set `PYTHONDONTWRITEBYTECODE=1`. Otherwise importing `driver/` creates `third_party/downward/driver/__pycache__/`. That directory is gitignored, but it's still a write into the submodule.

**Translator errors:** these go to stdout, for example "Undefined object / Got: b" or "Invalid requirement". Translator *crashes* show up on stderr as a `b'Traceback …'` blob. Capture both streams.

## 3. Plan file format

This is the actual output for the test task in section 9:

```
(walk a b)
(walk b c)
(walk c d)
; cost = 3 (general cost)
```

- **Step lines:** one action per line, `(<action> <arg> …)`, with all names lowercased. `Walk-Fast` / `Alpha` come out as `walk-fast` / `alpha`; this was tested.
- **Trailer:** the last line always matches `^; cost = (\d+) \((unit cost|general cost)\)$`. That is the same regex the driver's `plan_manager.py` uses.
  - `unit cost` means *every* operator in the task has cost 1. It does not mean "no metric".
  - Without `:metric`, all costs become 1, so you get `unit cost`.
  - A metric task whose action costs are all 1 also says `unit cost`.
- **Completeness:** the driver treats a plan file without this trailer as incomplete.
- **stdout:** the search also prints `<action> (<cost>)` per step and `Plan cost: N` there.

## 4. Exit codes

These come from `driver/returncodes.py` and `docs/exit-codes.md`, which agree. **Tested** means the code was actually triggered in this investigation.

| Code | Name | Meaning | Tested with |
| --- | --- | --- | --- |
| 0 | SUCCESS | plan found (optimal for `astar(lmcut())`) | yes, baseline |
| 1-3 | SEARCH_PLAN_FOUND_AND_… | portfolios only | n/a |
| 10 | TRANSLATE_UNSOLVABLE | "currently not used" | n/a |
| 11 | SEARCH_UNSOLVABLE | proved unsolvable | **yes**, `variants/unsolvable` |
| 12 | SEARCH_UNSOLVED_INCOMPLETE | incomplete search gave up (e.g. `astar(..., max_time=…)`) | no |
| 13 | SEARCH_UNSOLVABLE_WITHIN_BOUND | no plan under `bound=` | no |
| 20 | TRANSLATE_OUT_OF_MEMORY | translator out of memory | **yes**, `--overall-memory-limit 60M` on satellite p25 |
| 21 | TRANSLATE_OUT_OF_TIME | translator out of time | **yes**, `--overall-time-limit 5s` on satellite p25 |
| 22 | SEARCH_OUT_OF_MEMORY | search out of memory ("Failed to allocate memory.") | **yes**, `--search-memory-limit 100M` with `astar(blind())` |
| 23 | SEARCH_OUT_OF_TIME | search hit its CPU limit (SIGXCPU, "caught signal 24") | **yes**, `--search-time-limit 5s` |
| 24 | SEARCH_OUT_OF_MEMORY_AND_TIME | portfolios only | n/a |
| 30 | TRANSLATE_CRITICAL_ERROR | translator bug or assertion, incl. some malformed PDDL | **yes**, cost `increase` inside `when` triggers an AssertionError |
| 31 | TRANSLATE_INPUT_ERROR | bad PDDL or bad translator option | **yes**, undeclared object; `:numeric-fluents` requirement |
| 32 | SEARCH_CRITICAL_ERROR | planner bug | no |
| 33 | SEARCH_INPUT_ERROR | bad search options or SAS file, or plan file not writable | no |
| 34 | SEARCH_UNSUPPORTED | feature unsupported by the configuration | **yes**, conditional effects or axioms with lmcut |
| 35 | DRIVER_CRITICAL_ERROR | driver failure (e.g. setting rlimits) | no |
| 36 | DRIVER_INPUT_ERROR | bad driver args, missing files or build dir | **yes**, `--build …/bin` |
| 37 | DRIVER_UNSUPPORTED | e.g. memory limits on macOS | n/a on Linux |

**Signals:** if the search is killed by any other signal N (e.g. SIGTERM, SIGKILL), the driver logs `search exit code: -N` and calls `sys.exit(-N)`. The caller then sees 256−N: SIGTERM gives 241 (tested, also through `uv run`), and SIGKILL would give 247. 247 can also mean a time limit. The hard `RLIMIT_CPU` is T+1 s, so if the SIGXCPU shutdown doesn't finish in time, the kernel SIGKILLs the process. If the *driver* process itself is killed, e.g. by the OOM killer or your own kill, `Popen.returncode` is negative (`-N`).

**For an orchestrator:**

- 0: success.
- 11: definitively no plan.
- 20 to 23: resource exhaustion.
- 30 to 37: bug or bad input.
- Anything else: killed by a signal.

`uv run` passes all of these through unchanged; tested with 0, 11, 20 to 23, 30, 31, 34, 36 and 241.

## 5. Time and memory limits

Driver options, placed before the input files, from `driver/arguments.py` and `driver/limits.py`:

```
--overall-time-limit T     --overall-memory-limit M
--translate-time-limit T   --translate-memory-limit M
--search-time-limit T      --search-memory-limit M
--validate-time-limit T    --validate-memory-limit M
```

- **Units:** time is in seconds by default, with suffixes `s`, `m`, `h` (e.g. `90s`, `5m`). Memory is in MiB by default, with suffixes `K`, `M`, `G` (e.g. `2G`).
- **Default:** none. All limits are inactive unless set; only external `ulimit`s apply.
- **Effective limit per component:** the minimum of the component limit and the overall limit.
  - The overall time limit is a budget shared across components. The search gets whatever CPU time the translator and the driver left over.
  - In the tested example, `--overall-time-limit 5s` resulted in `translator time limit: 4s`, and the translator for satellite p25 (≈5.2 s CPU) died with exit code 21. Put generous margins on overall limits when translation is non-trivial.

Time limits are CPU seconds, not wall clock. The driver uses `RLIMIT_CPU` (soft = T, hard = T+1), and a soft-limit SIGXCPU is turned into exit 23 (search) or 21 (translator). Memory limits are `RLIMIT_AS` (virtual address space), not resident memory. These limits don't bound wall-clock time: a process blocked on I/O or starved by load can exceed T in wall time, so the orchestrator should add its own wall-clock timeout (see section 9). `astar(..., max_time=…)` is not a substitute, because its help says it is checked only between expansions and "should not be used for time-limiting experiments".

The tiny test task peaks at about 12 MB in search and takes about 0.5 s end to end. The translator's Python startup dominates; it's ~0.44 s without the `uv` wrapper. A suggested starting point is `--overall-time-limit 60s --overall-memory-limit 2G`.

## 6. PDDL feature support (with `astar(lmcut())`)

**What FD supports:**

- From `docs/pddl-support.md`: PDDL 2.2 level 1 plus `:action-costs`, i.e. STRIPS + ADL + axioms/derived predicates + action costs.
- Not supported: numeric fluents (beyond total-cost), temporal planning, preferences or soft goals, object fluents, and `(either …)` types.

**What lmcut supports:** per `bin/downward --help --txt2tags lmcut` and the website Evaluator page:

- action costs: **supported**
- conditional effects: **not supported**
- axioms: **not supported**
- admissible yes, consistent no, safe yes

**What compiles to axioms:** some PDDL features compile into axioms, so lmcut rejects them too. Each feature was tested on a fluent predicate so the translator couldn't simplify it away; the probes are in the scratchpad (section 10). The "Translator result" column shows what the translator produced (SAS ops, cond-eff ops, axioms), and "lmcut result" is the end-to-end exit code.

| Feature (`:requirements` label) | Where used | Translator result | lmcut result |
| --- | --- | --- | --- |
| `:strips` | | plain | ✅ 0 |
| `:typing` | types and typed params | compiled into static type predicates | ✅ 0 |
| `:negative-preconditions` | precondition `(not (visited ?to))` (binary fluent) | direct SAS precondition | ✅ 0 |
| `:negative-preconditions` | precondition `(not (at ?to))` (multi-valued variable) | still 4 ops | ✅ 0 |
| negative literal in **goal** | `(:goal (and (at d) (not (visited c))))` | direct goal fact, 0 axioms | ✅ 0, cost 10 (correct) |
| `:equality` | `(not (= ?from ?to))` | evaluated at grounding | ✅ 0 |
| `:disjunctive-preconditions` | **precondition** `(or (not (visited ?to)) (has-pass))` | split into separate operators (4 → 8), 0 axioms | ✅ 0 |
| `:existential-preconditions` | **precondition** `(exists (?l) (and (visited ?l) (path ?l ?to)))` | becomes extra action parameter, 0 axioms | ✅ 0 |
| `:disjunctive-preconditions` | **goal** `(or (at d) (at e))` | **2 axioms** | ❌ **34** "does not support axioms" |
| `:existential-preconditions` | **goal** `(exists (?l) (and (at ?l) (path c ?l)))` | **1 axiom** | ❌ **34** |
| `:disjunctive-preconditions` | **precondition** `(imply (visited ?from) (not (visited ?to)))` | rewritten as `or`, split (4 → 6 ops), 0 axioms | ✅ 0 |
| `:universal-preconditions` | precondition `(forall (?l) (or …))` | **2 axioms** (documented: universal conditions → axioms) | ❌ **34** |
| universal **effect** (no `when`) | effect `(forall (?l - location) (not (visited ?l)))` | expanded at grounding, 0 conditional effects | ✅ 0 |
| `:derived-predicates` | `(:derived …)` used in a precondition | **1 axiom** | ❌ **34** |
| `:conditional-effects` | `(when (visited b) (tired))` | 2 operators keep conditional effects | ❌ **34** "does not support conditional effects (operator walk b c)" |
| `:action-costs` | `(increase (total-cost) 10)` with `(:metric minimize (total-cost))` | per-op cost | ✅ 0, cheapest plan chosen |
| `:action-costs` | cost from a **static** function: `(increase (total-cost) (road-len ?from ?to))`, `(= (road-len a d) 2)` in `:init` | per-op cost | ✅ 0 |
| `:action-costs` | `increase` **inside `when`** | translator AssertionError | ❌ **30** |
| `:action-costs` without `:metric` | | costs **ignored**, every action costs 1 | ⚠️ 0, but it picks the *shortest* plan: `; cost = 1 (unit cost)` |
| `:action-costs` with an action that has **no** `increase` | | that action costs **0** (with `:metric`) | ⚠️ 0, `; cost = 0` |
| `:numeric-fluents` (label) | in `:requirements` | "Invalid requirement" | ❌ **31** |

**Other observations:**

- **Requirement checking:** `:requirements` is checked only against a whitelist of labels: `:strips :adl :typing :negation :equality :negative-preconditions :disjunctive-preconditions :existential-preconditions :universal-preconditions :quantified-preconditions :conditional-effects :derived-predicates :action-costs`. Features are not gated by what you declare: a domain declaring only `:strips` that uses typing, negation and costs ran fine. An unknown label such as `:numeric-fluents` or `:fluents` is a hard error.
- **Domain constants:** objects referenced inside the domain must be declared in `(:constants …)`. Otherwise you get exit 31, "Undefined object".
- **Action-cost restrictions** (`docs/pddl-support.md`):
  - Costs must be non-negative integers.
  - Each action may have at most one `total-cost` effect.
  - That effect may not sit inside a conditional effect.
  - Only `(:metric minimize (total-cost))` is accepted as a metric.

## 7. Recommended PDDL subset for our hand-written domain

To keep `astar(lmcut())` running and optimal:

**Use freely:**

- `:strips`, `:typing`
- `:negative-preconditions`: negated literals in preconditions *and* in goals
- `:equality`
- `:action-costs`, with exactly one `(increase (total-cost) N)` per action, where `N` is a non-negative integer constant or a static function set in `:init`. Always put `(:metric minimize (total-cost))` in the problem.
- Domain objects declared as `(:constants …)`.

**OK in preconditions only:**

- `(or …)` / `(imply …)`: the translator splits them into multiple operators, which can blow up the operator count.
- `(exists …)`: it becomes extra parameters.
- Keep all of these out of goals; there they turn into axioms.

**OK in effects:**

- An unconditional `(forall (?x - t) <literal>)` effect is expanded at grounding.

**Avoid:**

- `when` (conditional effects)
- `forall` in any *condition* (preconditions or goals)
- `or` / `exists` in the goal
- `:derived` predicates
- any numeric fluent other than `total-cost`
- `(either …)` types
- costs inside `when`

Model what you'd write as a conditional effect as separate actions with mutually exclusive preconditions instead.

**Every action must carry an explicit cost.** An action without `increase` silently costs 0 under a metric.

**Sanity check per domain:** run once and confirm exit 0 and a `; cost = … (general cost)` trailer. If any action is meant to cost ≠ 1, the trailer must say `general cost`. A `unit cost` trailer means the metric was missing.

## 8. Python version

The driver has no version check. The translator's `pyproject.toml` says `requires-python = ">=3.9"`, and the README test matrix lists 3.9, 3.10 and 3.14. The driver and translator import only the standard library (`pytest` appears only in the driver's tests).

The driver launches the translator as `sys.executable -m fast_downward.translate` with `PYTHONPATH=<build>/bin`, so the translator runs under whatever interpreter runs the driver; it's not a separate install.

Python 3.12 works. It was tested end to end with `uv run --no-project --python 3.12 python fast-downward.py …`, using cpython 3.12.13 from uv's managed pythons. The log line confirms it: `translator command line string: …/cpython-3.12-linux-x86_64-gnu/bin/python3.12 -m fast_downward.translate …`.

Inside a uv project, plain `uv run python …` uses the project venv interpreter, which is fine as long as it is ≥ 3.9. From the orchestrator, call the driver with `sys.executable` (as the wrapper in section 9 does) to skip `uv` startup per plan.

## 9. Copy-pasteable example

**Test task** (both files are in the scratchpad, see section 10). The shortest plan is `(drive a d)` at cost 10. The cheapest is three `walk`s at cost 3.

```lisp
;; domain.pddl
(define (domain travel)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types location)
  (:predicates (at ?l - location) (road ?from ?to - location)
               (path ?from ?to - location) (visited ?l - location))
  (:functions (total-cost) - number)
  (:action drive
    :parameters (?from ?to - location)
    :precondition (and (at ?from) (road ?from ?to) (not (visited ?to)))
    :effect (and (not (at ?from)) (at ?to) (visited ?to) (increase (total-cost) 10)))
  (:action walk
    :parameters (?from ?to - location)
    :precondition (and (at ?from) (path ?from ?to) (not (visited ?to)))
    :effect (and (not (at ?from)) (at ?to) (visited ?to) (increase (total-cost) 1))))
```

```lisp
;; problem.pddl
(define (problem travel-1)
  (:domain travel)
  (:objects a b c d - location)
  (:init (at a) (visited a) (road a d) (path a b) (path b c) (path c d)
         (= (total-cost) 0))
  (:goal (at d))
  (:metric minimize (total-cost)))
```

**Shell:**

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python 3.12 python \
  /home/ilyask/projects/fast-mi/third_party/downward/fast-downward.py \
  --build /home/ilyask/projects/fast-mi/build/downward/release \
  --overall-time-limit 60s --overall-memory-limit 2G \
  --plan-file /tmp/travel.plan \
  domain.pddl problem.pddl --search "astar(lmcut())"
echo "exit=$?"; cat /tmp/travel.plan
# exit=0
# (walk a b)
# (walk b c)
# (walk c d)
# ; cost = 3 (general cost)
```

The same run with `--alias seq-opt-lmcut` in place of `--search "astar(lmcut())"` gives the identical plan. Dropping the `:metric` line gives `(drive a d)` / `; cost = 1 (unit cost)`.

**Python wrapper:** it has been tested to return `plan`, `unsolvable` (11), `unsupported-feature` (34), `search-timeout` (23) and `wall-timeout`, with no orphans left behind. It uses `start_new_session` + `killpg` because killing only the top-level process, e.g. via `subprocess.run(timeout=…)`, leaves `bin/downward` running as an orphan (tested). Killing the process group removes everything.

```python
from __future__ import annotations
import os, re, signal, subprocess, sys, tempfile
from dataclasses import dataclass
from pathlib import Path

FD = Path("/home/ilyask/projects/fast-mi/third_party/downward/fast-downward.py")
BUILD = Path("/home/ilyask/projects/fast-mi/build/downward/release")  # NOT .../bin
TRAILER = re.compile(r"^; cost = (\d+) \((unit cost|general cost)\)$")
OUTCOME = {0: "plan", 11: "unsolvable", 12: "incomplete", 13: "unsolvable-within-bound",
           20: "translate-oom", 21: "translate-timeout", 22: "search-oom",
           23: "search-timeout", 30: "translate-crash", 31: "translate-input-error",
           32: "search-crash", 33: "search-input-error", 34: "unsupported-feature",
           35: "driver-crash", 36: "driver-input-error", 37: "driver-unsupported"}

@dataclass
class Result:
    returncode: int | None              # None = killed by our wall-clock timeout
    outcome: str
    plan: list[tuple[str, ...]] | None  # [("walk", "a", "b"), ...]  (FD lowercases names)
    cost: int | None
    log: str                            # stdout+stderr; translator errors are on stdout

def solve(domain: Path, problem: Path, *, cpu_limit="60s", mem_limit="2G",
          wall_timeout=120.0) -> Result:
    with tempfile.TemporaryDirectory(prefix="fd-") as tmp:  # isolates output.sas / plan per run
        plan_file = Path(tmp) / "plan"
        cmd = [sys.executable, str(FD), "--build", str(BUILD),
               "--overall-time-limit", cpu_limit, "--overall-memory-limit", mem_limit,
               "--plan-file", str(plan_file),
               str(Path(domain).resolve()), str(Path(problem).resolve()),
               "--search", "astar(lmcut())"]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.Popen(cmd, cwd=tmp, env=env, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
        try:
            log, _ = p.communicate(timeout=wall_timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)          # driver AND bin/downward
            log, _ = p.communicate()
            return Result(None, "wall-timeout", None, None, log)
        rc = p.returncode
        if rc < 0:                                    # driver itself killed by signal -rc
            outcome = f"killed-by-signal-{-rc}"
        else:                                         # 256-N: search killed by signal N (247 may be a CPU-limit SIGKILL)
            outcome = OUTCOME.get(rc, f"killed-by-signal-{256 - rc}" if rc > 128 else f"unknown-{rc}")
        if rc != 0:
            return Result(rc, outcome, None, None, log)
        lines = plan_file.read_text().splitlines()
        m = TRAILER.match(lines[-1])
        assert m, f"incomplete plan file: {lines[-1]!r}"
        steps = [tuple(l.strip("()").split()) for l in lines[:-1]]
        return Result(rc, outcome, steps, int(m.group(1)), log)
```

## 10. Artefacts from this investigation

All test artefacts are in the session scratchpad, which is not durable. Copy them if you need them.

`/tmp/claude-1000/-home-ilyask-projects-fast-mi/975d25c5-1c4c-46c0-99d6-f3d27f274bd2/scratchpad/fd/` contains:

- `domain.pddl`, `problem.pddl`: the test task above.
- `gen_variants.py` → `variants/<feature>/`: feature probes. `run_variants.py translate|search` re-runs them and prints the SAS stats and exit codes.
- `limits_test.sh`: the time and memory limit exit codes (satellite p25).
- `proc_test.py`: the orphan, `killpg` and signal exit-code checks.
- `fd_runner.py`: the wrapper above.

The build log is at `/home/ilyask/projects/fast-mi/build/downward/build-release.log`.
