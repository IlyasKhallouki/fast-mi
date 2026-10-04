# Fast Downward with time costs: support, limits and context keying

- **Question:** Phase 8 (`docs/plan.md`, Task 8.1, "Fast Downward"). Can `astar(lmcut())` plan on measured ticks instead of action counts? How expensive is keying costs by the room ego entered from?
- **Planner:** submodule `third_party/downward`, tag `release-26.6.0` (commit `7ea2755`), existing build `build/downward/release`. Nothing was rebuilt.
- **Builds on:** `docs/research/fast-downward.md`, which covers the build, the driver, exit codes and the PDDL subset. This note does not repeat those.
- **Verified by running:** on 2026-10-04, on a 4-core/8-thread laptop i5-8350U with frequency scaling, alongside other workflow jobs (load average 5–10).
  - **Expansion and operator counts** are deterministic, so they are the primary metrics.
  - **Times** are FD's own *process CPU* seconds (`third_party/downward/src/search/utils/timer.cc:82`, `CLOCK_PROCESS_CPUTIME_ID`). Even so, they moved by up to 2× with machine load, so read them as ratios.
- **The current plan was read, not regenerated.** I did not run `uv run speedrun plan part1`, because it writes `out/plans/part1.*` and this task was read-only. I read the existing `out/plans/part1.sas_plan` and `.log` (66 actions, unit cost), and ran FD directly on a hashed scratchpad snapshot of `pddl/part1/` (§3.2).
- **Scripts and raw results:** in the session scratchpad (§7), which is not durable.

## TL;DR

1. **Costs.** `astar(lmcut())` accepts both kinds:
   - per-action integer constants, `(increase (total-cost) 3750)`;
   - static functions, `(increase (total-cost) (walk-cost ?from ?to))` with `(= (walk-cost a b) 123)` in `:init`.

   50,000 per action and about 200,000 per plan is far inside the limits. Five sharp edges:
   - **Missing value.** If an action's cost function has no value in `:init`, the translator *silently deletes* that ground action. You get no error and no warning, just exit 0 and a different plan (§1.2).
   - **g overflow.** The search stores g in a **30-bit** bit-field (`third_party/downward/src/search/search_node_info.h:19`). Path costs must stay below **2^29 − 1 = 536,870,911**. Above that, g wraps without any check, and FD returns a *wrong* plan with exit 0 (tested, §1.3). Our scale has about 1,000× headroom.
   - **Value format.** Fractional or negative values are rejected (exit 31), and so is any value above 2^31−1 (exit 33).
   - **No arithmetic.** An expression such as `(+ (walk-cost ?a ?b) 9492)` crashes the translator (exit 30). Precompute the sums.
   - **Speed.** Magnitude doesn't matter, but cost *diversity* does. On the real model, tick costs needed fewer expansions than unit costs (1.8k–7.2k vs 16.5k), but each expansion took about 2× longer. Each timed run took 0.6–2.4 s (§1.4).
2. **Optimality holds.** I checked 840 encoding × world runs against an independent Dijkstra on a hand-written semantic model, plus `astar(blind())`, plus a replay of every plan. The worlds were random toys with gates, alternative recipes, a one-shot +9,492 cutscene, 0- and 1-cost actions, and totals of 25k–174k. There were **0 mismatches** (§2).
3. **Context keying is expensive if done everywhere, cheap if done selectively.** On a 50-room/150-link toy:
   - **Global** `(entered-from ?e)` keying multiplies ground operators by about 3.8× and expansions by about 2.7–4.7× (median). It costs **about 13–35× search time** (median; up to 75×).
   - **Without a static `(ctx-of ?e ?r)` filter**, 8,417 operators were grounded, and the search hit the 600 s limit without a plan.
   - **Selective** keying (context recorded only while ego is in the ≈10% of rooms that need it) costs **about 1.1× expansions (0.9–1.8×) and 1.6× time (1.1–2.3×)**.
   - **Real part1 model** (snapshot, 3 cost draws):
     - timed and unkeyed: 0.6–2.4 s;
     - selective, 4 keyed rooms: +22–31% expansions, 1.3–2.0× time;
     - global keying: 2.0–2.5× expansions, 5.7–7.7× time, 5–17 s (§3).

     Peak search memory never exceeded 22 MB.
4. **Recommendation.**
   - Use the §4(a) encoding (constants plus `walk-cost`) for every action.
   - Key only the rooms whose actions show large context variance, with the §4(b) encoding: `entered-from` plus `ctx-of` plus `next-ctx`, with the context parameters last.
   - Both keep exactly the current requirements line:

     ```lisp
     (:requirements :strips :typing :negative-preconditions :action-costs)
     ```

---

## 1. Integer and function costs with `astar(lmcut())`

### 1.1 What is supported, from the source

| Stage | Behavior | Source |
|---|---|---|
| Parse | A cost is a digit string (→ `NumericConstant`), or a list (→ function term). A leading `-` gives "Negative numbers are not allowed". `12.5` gives "Fractional numbers are not supported". | `third_party/downward/src/translate/fast_downward/translate/pddl_parser/parsing_functions.py:434-450` |
| Parse | `NumericConstant` rejects non-integers again. | `third_party/downward/src/translate/fast_downward/translate/pddl/f_expression.py:15-20` |
| Parse | `:init` assignments must be constants. | `third_party/downward/src/translate/fast_downward/translate/pddl_parser/parsing_functions.py:578-584` |
| Ground | With `:metric`, the cost is `int(<instantiated cost>)`, and an action with no `increase` costs 0. Without `:metric`, the cost is 1. | `third_party/downward/src/translate/fast_downward/translate/pddl/actions.py:98-105` |
| Ground | A function-valued cost adds an implicit precondition `@def-<fn>(args)`, which only `:init` assignments make true. **A ground action whose cost has no value is never instantiated.** | `third_party/downward/src/translate/fast_downward/translate/normalize.py:29-41`, `:135-136`, `:486-489`; `third_party/downward/src/translate/fast_downward/translate/pddl_to_prolog.py:158-161` |
| Write SAS | `assert self.cost >= 0 and self.cost == int(self.cost)` | `third_party/downward/src/translate/fast_downward/translate/sas_tasks.py:374` |
| Read SAS | `stoi`. Out of range gives "Could not parse … (out of range)". A negative cost is an error. | `third_party/downward/src/search/tasks/root_task.cc:220-240`, `:467-473` |
| Search g | `int g : 30` (signed 30-bit) plus `int real_g`. Updated as `info.g = parent.g + cost` with no overflow check. | `third_party/downward/src/search/search_node_info.h:19,22`, `third_party/downward/src/search/search_space.cc:59-60`, `third_party/downward/src/search/search_algorithms/eager_search.cc:252` |
| f = g + h | `int`. Overflow is guarded only by an `assert`, which Release compiles out. | `third_party/downward/src/search/evaluators/sum_evaluator.cc:17-25` |
| Open list | `std::map<vector<int>, deque>` keyed by [f, h]. Memory and time don't depend on cost magnitude. | `third_party/downward/src/search/open_lists/tiebreaking_open_list.cc:21`; `third_party/downward/src/search/search_algorithms/search_common.cc:111-129` |
| lmcut | All costs are `int`. Each round subtracts the cut's minimum cost, so at least one operator drops to 0. Rounds are bounded by the operator count, not the cost magnitude. | `third_party/downward/src/search/heuristics/lm_cut_landmarks.h:34-38`, `third_party/downward/src/search/heuristics/lm_cut_landmarks.cc:333-342` |
| lmcut queue | The `AdaptiveQueue` starts as a bucket queue and turns into a binary heap once a key is ≥ 100 and exceeds the push count. With tick costs it is always a heap: O(log n) per push instead of O(1). | `third_party/downward/src/search/algorithms/priority_queues.h:137`, `:224-233` |
| Optimality | `astar` forces `reopen_closed=true`. lmcut is documented as admissible (not consistent) with action costs supported. | `third_party/downward/src/search/search_algorithms/plugin_astar.cc:52`; `third_party/downward/src/search/heuristics/lm_cut_heuristic.cc:72-78` |

### 1.2 Probes

Each probe below is a 5-room task with walks priced by `walk-cost` and three 0-ary actions priced by constants. The constants range from 1 to 50,000, so cost-1 and cost-50,000 actions share one task, as they will in Task 8.4's optimistic loop. Every probe below, plus the §4(b) `forall` probe, was run with both `astar(lmcut())` and `astar(blind())`, and the two agreed in every case.

| Probe | Result |
|---|---|
| Constants 1 / 3750 / 50000, function costs 7 … 50000 | exit 0, `; cost = 85751 (general cost)`: the cheaper of two routes |
| Same, total pushed to 142,201 | exit 0, correct route, `general cost` |
| Constant object as a function argument, `(increase (total-cost) (kc c))` | exit 0, correct |
| `(= (walk-cost a b) 1200.5)` in `:init` | exit **31**, "Fractional numbers are not supported." |
| `(increase (total-cost) 3750.0)` | exit **31**, same message |
| `(= (walk-cost a b) -5)` | exit **31**, "Negative numbers are not allowed." |
| `(increase (total-cost) (+ (walk-cost ?a ?b) 9492))` | exit **30**: translator `TypeError` (the list is read as a function name) |
| Constant 3,000,000,000 (> 2^31−1) | exit **33**: "Could not parse '3000000000' as integer (out of range)." |
| **`walk-cost c d` omitted** for a reachable `(link c d)` | **exit 0, no warning.** The translator reports 10 operators instead of 11, `walk c d` is gone, and the plan switches to the costlier route (142,201 instead of 85,751). The `assert … "Could not find instantiation for PNE"` at `third_party/downward/src/translate/fast_downward/translate/pddl/f_expression.py:54` is never reached. |
| **Misspelled object in a cost fact**: `(= (walk-cost c dd) 2000)`, where `dd` is not a declared object | **exit 0, no error.** The fact is accepted, `walk c d` has no value and is pruned (10 operators), and the result is the same wrong plan as above. |
| `walk-cost` given for a declared pair with no `link`, `(= (walk-cost e a) 5)` | ignored, exit 0, 11 operators |

The silent pruning in the two bold rows is what matters for `speedrun.costing`. A forgotten or misspelled `walk-cost` fact quietly deletes a walk from the model, and the optimiser then "proves" a route optimal over a smaller graph. The guard is in §4(a).

### 1.3 Overflow limits

| Quantity | Type | Limit | When it is exceeded |
|---|---|---|---|
| One action's cost | `int` | 2,147,483,647 | exit 33 at SAS read: safe and loud |
| g of any **generated** node | `int g : 30` | **536,870,911** | **silent wrap-around** |
| f = g + h, and h (lmcut sum) | `int` | 2,147,483,647 | assert only (Release: silent) |

The probe is a chain a→b→c→d, three walks of W each, against a direct a→d walk of D:

| W, D | True optimum | FD result |
|---|---|---|
| 178,956,970 ×3, D = 536,870,911 | chain, 536,870,910 | correct, exit 0 |
| 178,956,971 ×3, D = 536,870,911 | direct, 536,870,911 | correct, exit 0 (by luck) |
| **1,000 ×3, D = 600,000,000** | **chain, 3,000** | **wrong: `(walk a d)`, `; cost = 600000000`, exit 0.** g wrapped to −473,741,824, so the expensive edge looked cheapest. |
| (first attempt) decoy edges of 2·10^9 | n/a | "Solution found!", then "Failed to allocate memory", exit **22**. The log shows a goal with wrapped g (208,516,356) after a reopening. The most likely cause is a parent-pointer cycle during plan extraction. |

**What we need.** A* with an admissible h expands only nodes with f ≤ C\*, so every generated g is at most C\* + max operator cost. Our totals and their headroom against 536,870,911:

| Scope | Ticks (1/60 s) | Headroom |
|---|---|---|
| Part I segment | about 2·10^5 | about 2,600× |
| Whole game (2 h) | about 4.3·10^5 | about 1,200× |
| Whole game in 1/600 s units | about 4.3·10^6 | about 120× |

The cheap, sound guard for the costing module:

```python
UB = cost of any valid plan under the table   # e.g. the current plan, priced
assert UB + max(op costs) < 2**29, "FD g-value would overflow (search_node_info.h:19)"
```

### 1.4 Performance with tick-sized costs

- **Magnitude is irrelevant to the algorithms.** Nothing scales with the cost value itself: see the open list and lmcut rows in §1.1. Probes with costs from 10^3 to 5·10^8 all solved in milliseconds.
- **Diversity costs time per node.** With unit costs, one lmcut cut zeroes every operator in it. With distinct costs, each round zeroes only the cheapest, so the heuristic runs more rounds per state.
- **Real part1 model** (snapshot of `pddl/part1/`, §3.2, three random draws): tick costs (walks 100–3,000, guarded transitions 300–6,000, other actions 300–20,000, plus 9,492 on the two "meanwhile" exits) versus unit cost:

| Costs | h0 / C\* | Expanded | Search CPU s | ms per expansion |
|---|---|---|---|---|
| unit, as committed | 35 / 66 = 0.53 | 16,544 | 2.89 | 0.17 |
| ticks, seed 1 | 251,947 / 320,541 = 0.79 | 7,217 | 2.38 | 0.33 |
| ticks, seed 2 | 0.81 | 1,758 | 0.64 | 0.37 |
| ticks, seed 3 | 0.74 | 3,196 | 1.32 | 0.41 |
| half the actions at 1 tick, seed 1 | 0.73 | **56,176** | **12.91** | 0.23 |
| half the actions at 1 tick, seed 2 | 0.76 | 1,380 | 0.34 | 0.25 |
| half the actions at 1 tick, seed 3 | 0.81 | 5,215 | 1.34 | 0.26 |

The model has 227 ground operators in every row. These runs were serial on a quieter machine.

  - **Fewer expansions:** the tick-costed lmcut is better informed (h0/C\* 0.74–0.81 vs 0.53), because the big mandatory actions become heavy landmarks.
  - **Slower per node:** each expansion costs about 2× more (0.33–0.41 ms vs 0.17 ms).
  - **Net effect:** all of these are a few seconds, which is fine for Task 8.4's repeated re-plans.
- **Mixed cost-1 and real costs** (the optimistic loop, with half the actions still at the 1-tick lower bound): always correct and `general cost`. One draw needed 56k expansions and 13 s, because cheap placeholder actions weaken lmcut's landmarks. Budget for an occasional slow iteration; FD itself has no issue with mixing 1s and 50,000s.

## 2. Optimality with these costs

**Why it holds.**
- `astar` reopens closed nodes (`third_party/downward/src/search/search_algorithms/plugin_astar.cc:52`).
- lmcut is admissible for any non-negative integer costs (`third_party/downward/src/search/heuristics/lm_cut_heuristic.cc:76-77`).
- Costs reach the search unchanged as `int`.

The only threat is the g overflow in §1.3.

**Test.**
- **Generator:** `toy.py` builds random worlds with these parts:
  - rooms joined by directed links, some gated by an item;
  - one "cutscene room" whose first entry costs +9,492, modelled as separate first and later walk actions;
  - K items picked up by 0-ary constant-cost actions;
  - two alternative finish recipes;
  - a goal room;
  - 15–20% of costs set to 0 or 1 in the small set, so lmcut's zero-cost goal-plateau and border code paths are exercised.
- **Encodings:** every world was encoded six ways: U, K, Kflat, Kfree, S and spot (§3.1).
- **Oracle:** an independent Python model of the *intended* semantics, including the cost-per-context rules. It was solved by Dijkstra, and FD's plan was **replayed** on it step by step.

| Set | Worlds | Runs (× lmcut, blind) | Plan totals | Mismatches |
|---|---|---|---|---|
| small: 9 rooms, 22 links, 4 items, 2 gates, 0/1 costs | 100 | 600 | 25,461 – 135,063 | **0** |
| medium: 16 rooms, 40 links, 6 items, 3 gates, costs to 50,000 | 40 | 240 | 58,579 – 173,918 | **0** |

In every run:
- lmcut's plan cost equals blind's;
- both equal the Dijkstra optimum;
- both equal the replayed cost of the plan;
- the trailer says `general cost`.

This validates the planner *and* the keyed encodings in §4: the context bookkeeping charges each step exactly the cost the semantic model assigns it. Kflat (keyed encoding with unkeyed costs) and Kfree (keyed costs, no `ctx-of` filter) always reproduced the optimum of U and K respectively.

## 3. Cost of context keying

### 3.1 Encodings compared

| Name | State | Walk cost | Room-action cost |
|---|---|---|---|
| **U** | `(at ?r)` only | `(walk-cost ?a ?b)` | constant |
| **K** | `(entered-from ?e)`, updated by every room change | `(kwalk-cost ?a ?b ?e)` | `(pick-iN-cost ?e)` |
| **Kflat** | same as K | K's encoding, U's numbers: the pure state-space overhead | same |
| **Kfree** | K without the static `(ctx-of ?e ?r)` precondition | costs defined for every context | same |
| **S** (selective) | context recorded only while ego is in a keyed room (10% of rooms), `none` elsewhere | keyed only for walks out of keyed rooms | keyed only in keyed rooms |
| **spot** | like K, but a room action also sets the context to its own spot | `(kwalk-cost ?a ?b ?e)` | by context |

`spot` is the more faithful model of a walk's start position (§3.4).

Keyed costs were the unkeyed cost ±50% (uniform), drawn per context.

### 3.2 Results

**Toy:** 50 rooms, 150 directed links, 12 items, 3 gates, one cutscene room, 5 random worlds. Each search time is the median of 3 repetitions. Plan totals run from 139,993 to 226,326. All 25 plans replayed to their reported cost on the semantic model. Times were taken under varying machine load (seed 1 alongside my other FD runs), which is why the time ranges are wide.

| Encoding | Ground ops (range) | Expanded, median (range) | Expanded vs U, median (range) | Search s, median (range) | Search vs U, median (range) | Peak KB | Translator CPU s |
|---|---|---|---|---|---|---|---|
| U | 167 (166–170) | 1,602 (926–3,976) | 1× | 0.66 (0.33–1.42) | 1× | 13,460 | 0.03 |
| **S** (10% of rooms keyed) | 206 (192–231) | 1,752 (874–4,280) | **1.1× (0.9–1.8)** | 1.23 (0.52–1.97) | **1.6× (1.1–2.3)** | 13,588 | 0.07 |
| Kflat | 624 (619–634) | 4,316 (1,927–11,297) | 2.7× (2.1–2.8) | 16.6 (3.9–19.4) | 13.5× (11.5–25) | 15,032 | 0.13 |
| K | 624 (619–634) | 7,496 (5,376–13,840) | 4.7× (3.2–12.6) | 25.0 (15.1–46.2) | 34.6× (25.7–74.8) | 16,052 | 0.16 |
| spot | 681 (668–686) | 6,999 (2,978–11,689) | 4.4× (1.7–12.2) | 19.5 (12.6–37.6) | 26.5× (14.5–88.1) | 15,932 | 0.13 |

**Kfree** (one world, k = 12):
- 8,417 ground operators;
- exit 23: CPU limit at 600 s;
- reached f = 184,813 of the true 190,011 after 11,545 expansions, about 52 ms per expansion.

**Reachable-state growth** (Dijkstra states touched before the goal, §2 worlds, median over worlds):

| Encoding | States vs U, small set | States vs U, medium set | Ground ops vs U, medium set |
|---|---|---|---|
| K | 2.2× | 2.4× | 3.1× |
| Kflat | 2.2× | 2.3× | 3.1× |
| S | 1.4× | 1.4× | 1.5× |
| spot | 2.4× | 2.5× | 3.5× |
| Kfree | n/a | n/a | 16.4× |

**Real part1 model.**
- **Snapshot:** `pddl/part1/domain.pddl` sha256 `436c0169…` and `problem.pddl` `9d18914c…`, copied just after a 22:05 edit, while Task 8.1b was still editing them: 75 schemas, 227 ground operators.
- **Transform:** done mechanically by `real/xform.py`. Every `walk*` action gets its from/to rooms from its `(at …)` literals.
- **Shape:** 39 rooms, 81 room-changing edges, mean 2.1 entries per room.
- **Keyed rooms in S:** `bar-left bar-right high-street-town mansion`.
- **Check:** T, Sflat and Kflat (encodings with unchanged numbers) returned the **identical** optimum for each seed. That confirms the transform.

| Encoding | Ground ops | SAS vars | Expanded (seeds 1 / 2 / 3) | Expanded vs T | Search CPU s (1 / 2 / 3) | Time vs T | Peak KB |
|---|---|---|---|---|---|---|---|
| T (timed, unkeyed) | 227 | 38 | 7,217 / 1,758 / 3,196 | 1× | 2.38 / 0.64 / 1.32 | 1× | 12,840–13,640 |
| Sflat (S encoding, T's numbers) | 260 | 39 | 8,975 / 2,276 / 4,082 | 1.24–1.29× | 4.27 / 1.30 / 1.90 | 1.4–2.0× | ≤ 14,048 |
| **S** (4 keyed rooms, ±50%) | 260 | 39 | 9,453 / 2,143 / 3,945 | **1.22–1.31×** | 4.26 / 1.28 / 1.75 | **1.3–2.0×** | ≤ 14,252 |
| Kflat (global keying, T's numbers) | 407 | 39 | 13,478 / 2,953 / 5,973 | 1.68–1.87× | 11.80 / 3.01 / 5.20 | 3.9–5.0× | ≤ 14,612 |
| K (global keying, ±50%) | 407 | 39 | 14,242 / 4,314 / 7,243 | 1.97–2.45× | 16.63 / 4.96 / 7.54 | 5.7–7.7× | ≤ 14,884 |
| S, half the actions at 1 tick | 260 | 39 | 68,312 / 1,619 / 6,727 | 1.17–1.29× (vs T at the same costs) | 21.95 / 0.63 / 2.64 | 1.7–2.0× | ≤ 21,500 |

These were serial runs, one per cell; times are FD process CPU seconds. Sflat and Kflat returned exactly T's optimal cost on every seed (320,541 / 279,236 / 207,670). S and K, whose costs differ per context, found plans 0.2–9% cheaper than T, as expected when the planner can choose cheaper contexts.

**Memory** was never an issue: peak search memory stayed at 13–22 MB in every run above. The FD process baseline is about 12 MB, and the translator about 54 MB.

### 3.3 Where the cost comes from

1. **Ground operators** multiply by the number of contexts per room: about 3.8× on the toy and 1.8× on the real model (mean 2.1 entries per room). lmcut's work per state grows with the operator count, and it grows more again when the context copies carry different costs, because each cut round then zeroes fewer copies.
2. **States** multiply by the contexts actually reachable per room: about 2.2–2.5× on the toys, while expansions grew 1.7–2.5× on the real model. A* can't tell that (room r, entered from x) and (room r, entered from y) are interchangeable for everything except cost.
3. **Heuristic dilution.** In the delete relaxation, every `(entered-from x)` is reachable at once, so lmcut prices each walk at its *cheapest* context. That is admissible, but weaker: h0 falls (e.g. 174,908 for K vs 203,540 for U on toy seed 1).
4. **The static filter is essential.** Without `(ctx-of ?e ?r)`, grounding is |contexts| × |links|. The PNE-definition rule (§1.2) also filters, if costs are emitted only for valid contexts, but then a forgotten fact silently deletes an operator.

**Selective keying** pays all three costs only inside the keyed rooms:
- outside them the context is the single value `none`;
- walks there ground once per link, as in U;
- only actions that *read* the context carry a `?e` parameter.

### 3.4 Fidelity caveat: what "entered from" actually keys

A step starts on the first sentence-idle frame after the previous step (`docs/plan.md` C4, "The flow for each step"). So a walk's duration depends on where the **previous step left ego**:

- After a walk into room r, ego stands at the entry point of the link it came through. Here `entered-from` is exact.
- After any room action in r, ego stands at that object's walk point (or wherever its script put him). `entered-from` is then stale for the next action in r.

So entry keying is exact only for the first action after entering a room. For the second and later actions in a keyed room, the faithful context is "the last action's spot". The `spot` variant implements this: a keyed room action also does `(not (entered-from ?e)) (entered-from spot-<action>)`. It cost about the same as K globally (table above). Applied selectively, it adds one context value per keyed action in the keyed rooms only. Whether to use it should come from the 8.3 measurements: key by previous step and see whether entry alone explains the variance.

## 4. Recommended encodings

Both target the **generated timed copy** (Task 8.3, `out/plans/<segment>-timed/`), not `pddl/part1/domain.pddl`. `tests/unit/test_pddl_model.py:286-287` (as of this writing; the file is being edited concurrently) pins the hand-written model to cost 1, and `:40`'s `ALLOWED_REQUIREMENTS` already admits everything below. Requirements line for both:

```lisp
(:requirements :strips :typing :negative-preconditions :action-costs)
```

The problem file must keep `(= (total-cost) 0)` and `(:metric minimize (total-cost))`. Without the metric, every cost silently becomes 1 (`third_party/downward/src/translate/fast_downward/translate/pddl/actions.py:105`).

### 4(a) Context-free mean costs

**Domain:** add one function, and replace each `(increase (total-cost) 1)`. In this and the next snippet, preconditions and other effects are copied unchanged from the snapshot; only the cost terms differ.

```lisp
  (:functions (total-cost) - number
              (walk-cost ?from ?to - room) - number)

  ;; generic walk: cost per static link, one value per (link ?from ?to)
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to) (not (store-door-open))
                       (not (cook-provoked)) (not (following-storekeeper)))
    :effect (and (not (at ?from)) (at ?to)
                 (increase (total-cost) (walk-cost ?from ?to))))

  ;; every 0-ary action: its rounded mean ticks as a constant
  (:action walk-into-bar
    :parameters ()
    :precondition (and (at dock) (bar-door-open) (not (following-storekeeper)))
    :effect (and (not (at dock)) (at bar-left) (cook-timer-fresh)
                 (increase (total-cost) 412)))

  ;; one-shot variants stay separate actions with their own constant
  (:action walk-out-of-bar-from-left-meanwhile
    :parameters ()
    :precondition (and (at bar-left) (not (lechuck-cutscene-seen)) (not (cook-provoked)))
    :effect (and (not (at bar-left)) (at dock) (lechuck-cutscene-seen)
                 (increase (total-cost) 9874)))
```

**Problem:** one value per link, placed next to it.

```lisp
  (:init
    (at dock)
    (= (total-cost) 0)
    (link dock lookout)          (= (walk-cost dock lookout) 287)
    (link dock low-street)       (= (walk-cost dock low-street) 455)
    (link bar-left bar-right)    (= (walk-cost bar-left bar-right) 96)
    ...)
  (:goal ...)
  (:metric minimize (total-cost))
```

The numbers are illustrative.

**Rules for `speedrun.costing`:**

1. **Integers only.** Write `round(mean)`, clamped at ≥ 0, never `287.4` (exit 31). For more resolution, scale every cost by the same factor; §1.3 leaves room for ×100.
2. **Exactly one `walk-cost` fact per `link` fact.**
   - Assert that the two key sets are equal before writing.
   - Validate every object name in every cost fact against the declared constants. The translator accepts an undeclared name such as `dd` without complaint.
   - After translation, assert that FD's `Translator operators: N` equals the unit-cost model's N.

   A missing or misspelled value silently deletes that walk (§1.2).
3. **Unmeasured actions.** In the optimistic loop they cost 1 (a valid lower bound); after measurement they cost their mean. A 0 is allowed but makes the action free (the 0-cost lmcut branches were tested in §2).
4. **No arithmetic in costs.** Precompute sums such as walk + cutscene (exit 30).
5. **Guard.** `UB + max_cost < 2**29` (§1.3).
6. **Check the trailer.** The plan's `; cost = N (general cost)` trailer must say `general cost`. `unit cost` means every cost was 1, i.e. the metric was lost.

### 4(b) Entry-room-keyed costs, only where context variance is large

- **Choose the keyed rooms.** Let KR be the set of rooms hosting any action whose variance across contexts exceeds its variance across seeds (the `docs/optimization.md` flag in Phase 8). In this encoding a context is recorded only while ego is in a room of KR. Everywhere else it is the constant `none`, so the state space and the ground operators outside KR are those of 4(a).
- **Where `?e` goes.** Only actions that read the context get the parameter, and it goes **last**: `?e - ctx`, or `?e ?n - ctx` for the generic walk.
- **Compiler mapping.** The compiler drops those trailing arguments to map a plan line back to its `steps.toml` key:

  | Plan line | Key |
  |---|---|
  | `(walk bar-left bar-right dock bar-left)` | `"walk bar-left bar-right"` |
  | `(open-store-door low-street)` | `"open-store-door"` |

```lisp
  (:types room - ctx ctx item)
  (:constants
    dock lookout ... f220 - room
    meat pot ... foyer-idol - item
    none segment-start - ctx)          ; none: not in a keyed room; segment-start: no entry yet

  (:predicates
    ...existing predicates...
    (entered-from ?e - ctx)                 ; current context (exactly one is true)
    (ctx-of ?e - ctx ?r - room)             ; static: ?e can be the context while ego is in ?r
    (next-ctx ?from ?to - room ?n - ctx))   ; static: context after (walk ?from ?to): ?from if ?to in KR, else none

  (:functions (total-cost) - number
              (kwalk-cost ?from ?to - room ?e - ctx) - number
              (cost-walk-out-of-bar-from-left ?e - ctx) - number   ; one per keyed action
              (cost-open-store-door ?e - ctx) - number)

  ;; generic walk: always keyed by (from, to, context); outside KR the context is none
  (:action walk
    :parameters (?from ?to - room ?e ?n - ctx)
    :precondition (and (at ?from) (link ?from ?to) (not (store-door-open))
                       (not (cook-provoked)) (not (following-storekeeper))
                       (entered-from ?e) (ctx-of ?e ?from) (next-ctx ?from ?to ?n))
    :effect (and (not (at ?from)) (at ?to)
                 (not (entered-from ?e)) (entered-from ?n)
                 (increase (total-cost) (kwalk-cost ?from ?to ?e))))

  ;; guarded transition from a plain room INTO a keyed room: no parameter needed,
  ;; because outside KR the context is always none
  (:action walk-into-bar
    :parameters ()
    :precondition (and (at dock) (bar-door-open) (not (following-storekeeper))
                       (entered-from none))
    :effect (and (not (at dock)) (at bar-left) (cook-timer-fresh)
                 (not (entered-from none)) (entered-from dock)
                 (increase (total-cost) 412)))

  ;; guarded transition OUT OF a keyed room: reads the context, so it gets ?e
  (:action walk-out-of-bar-from-left
    :parameters (?e - ctx)
    :precondition (and (at bar-left) (lechuck-cutscene-seen) (not (cook-provoked))
                       (entered-from ?e) (ctx-of ?e bar-left))
    :effect (and (not (at bar-left)) (at dock)
                 (not (entered-from ?e)) (entered-from none)
                 (increase (total-cost) (cost-walk-out-of-bar-from-left ?e))))

  ;; 0-ary room action in a keyed room: reads, does not change, the context
  ;; (ego walks to door 437 from wherever he entered high-street-town)
  (:action open-store-door
    :parameters (?e - ctx)
    :precondition (and (at high-street-town) (not (store-door-open)) (not (following-storekeeper))
                       (entered-from ?e) (ctx-of ?e high-street-town))
    :effect (and (store-door-open)
                 (increase (total-cost) (cost-open-store-door ?e))))

  ;; every other action (plain rooms, inventory-only actions): exactly as in 4(a)
```

```lisp
  (:init
    (at dock)
    (= (total-cost) 0)
    (entered-from none)                                ; dock is not in KR (else: segment-start)
    ;; ctx-of: none for every plain room; the entry rooms for every keyed room
    (ctx-of none dock) (ctx-of none lookout) ...
    ;; here KR = {bar-left, bar-right, high-street-town}
    (ctx-of dock bar-left) (ctx-of bar-right bar-left)       ; bar-left is entered from these
    (ctx-of bar-left bar-right) (ctx-of kitchen bar-right)   ; bar-right is entered from these
    (ctx-of low-street high-street-town) (ctx-of jail high-street-town)
    (ctx-of high-street-mansion high-street-town) (ctx-of store high-street-town)
    ;; next-ctx: one per link
    (next-ctx dock lookout none)
    (next-ctx bar-right bar-left bar-right)                  ; into keyed bar-left: remember bar-right
    (next-ctx bar-left bar-right bar-left)
    ;; kwalk-cost: one per (link, context of its from-room)
    (= (kwalk-cost dock lookout none) 287)
    (= (kwalk-cost bar-left bar-right dock) 140)             ; bar-left entered from the dock
    (= (kwalk-cost bar-left bar-right bar-right) 96)         ; bar-left entered through the curtain
    (= (cost-walk-out-of-bar-from-left dock) 1310)
    (= (cost-walk-out-of-bar-from-left bar-right) 1655)
    (= (cost-open-store-door low-street) 820)
    (= (cost-open-store-door jail) 610)                      ; ... one per entry of high-street-town
    ...)
```

The numbers and the per-room entry lists are illustrative. Generate them from the model as follows.

**Rules for the generator:**

1. **Entries come from every room-changing action.** A keyed room's entry set is its `link` sources **plus** the from-room of every `walk-*` action into it (the naming rule in `docs/part1/model.md` §1 makes these easy to find). Add `segment-start` if the segment starts in the room. Missing an entry makes that transition inapplicable, and the planner gives no warning.
2. **Every ground cost needs a value.** Emit `kwalk-cost` for the full product {link (a, b)} × {e : `ctx-of e a`}, and each `cost-<action>` for every context of the action's room.
   - Fill unmeasured contexts with the action's context-free mean, or 1 in the optimistic loop.
   - Validate the object names in every cost fact, and assert the fact counts.
   - **Operator-count guard.** Translate the generated keyed model a second time with every function-valued `(increase (total-cost) (fn …))` replaced by `(increase (total-cost) 1)`, and require the same `Translator operators` count. The only difference between the two runs is the implicit `@def-` precondition (§1.1), so equal counts mean no ground action was lost to a missing value. A fixed "expected count" doesn't work, because relaxed reachability legitimately prunes some instances.
3. **Keep the deletes precondition-fixed.** Every context delete is of a fact the precondition requires:
   - `(entered-from ?e)` for readers;
   - `(entered-from none)` for transitions from plain into keyed rooms.

   That keeps `entered-from` a single multi-valued SAS variable (39 vars on the real model, against 38 unkeyed) and avoids conditional effects (`docs/part1/model.md` §1). When both are `none`, the add and the delete cancel in favor of the add (tested in §2).
4. **Classify each guarded `walk-*` by its rooms.** The rooms are constants, so the generator emits one of three shapes:

   | From → to | Shape |
   |---|---|
   | plain → plain | unchanged |
   | plain → keyed | `(entered-from none)` → `(entered-from <from>)` |
   | keyed → any | `?e`; then `<from>` if the destination is keyed, `none` if not |

5. **Measurement keys.** A step in a keyed room is keyed by the source room of the room change that brought ego into that room. Read it from the trace's `step_end.changes.room`.
6. **Don't use global keying (§3.1 K).** It costs 13–35× search time on the toy (median) and 5.7–7.7× on the real model, and it buys nothing for rooms whose actions don't vary by context.

**Alternative, tested and not recommended.** `(forall (?x - ctx) (not (entered-from ?x)))` plus `(entered-from ?a)` lets an action *set* the context without a `?e` parameter. lmcut accepts it: exit 0, correct plan, no conditional effects, because `prune_stupid_effect_conditions` drops self-conditions on binary variables (`third_party/downward/src/translate/fast_downward/translate/main.py:330-344`). However:
- it only works because invariant synthesis gives up and splits `entered-from` into one binary variable per value;
- it puts `forall` in an effect, which the PDDL BNF ties to `:conditional-effects`;
- the selective encoding never needs it, since there only readers carry `?e`.

## 5. What this does not establish

- **Real-model times use random costs.** They are numbers on a snapshot of a model still under edit (Task 8.1b), with random tick-like costs, not measured ones. With the real 8.3 cost table, re-run the planner once and compare `Expanded` against the table above.
- **The toy is TSP-like.** It has 12 mandatory pickups in a 50-room graph. Its absolute times say little about part1, but its ratios show the trend.
- **Surrogate optimality only.** "Optimal" means optimal for the cost table we feed FD (`docs/plan.md` Phase 8). Nothing here addresses whether that surrogate is faithful; see §3.4.

## 6. Reproduce

```bash
S=/tmp/claude-1000/-home-ilyask-projects-fast-mi/975d25c5-1c4c-46c0-99d6-f3d27f274bd2/scratchpad/fdcosts
cd /home/ilyask/projects/fast-mi
uv run python $S/q1/gen.py          # §1.2 probes (lmcut + blind)
uv run python $S/q1/gbound.py       # §1.3 g-overflow probes
uv run python $S/q2/run_q2.py 0 100 # §2 small set; run_q2_med.py 1000 1040 for the medium set
uv run python $S/q3/bench.py '{"seeds":[1,2,3,4,5],"ks":[12],"variants":["U","Kflat","K","S","spot"],"reps":3}'
uv run python $S/real/run_real.py '{"seeds":[1,2,3],"modes":["T","Sflat","S","Kflat","K"]}'
```

`fdrun.py` passes `--plan-file`/`--sas-file` into each run directory and sets `PYTHONDONTWRITEBYTECODE=1`, so nothing is written to the repo or the submodule.

## 7. Artefacts

All of these are in the session scratchpad `…/scratchpad/fdcosts/`, which is not durable:

| Path | Contents |
|---|---|
| `fdrun.py` | FD runner and log parser |
| `toy.py` | world generator, the six encodings, semantic model, Dijkstra, plan replay |
| `q1/` | probes (§1) |
| `q2/results*.json` | per-run optimality data (§2) |
| `q3/main.jsonl`, `q3/probe/` | toy benchmark, including the Kfree run (§3) |
| `real/xform.py`, `real/snap/` | the real-model transform and the snapshot with its `SHA256` |
| `real/*.jsonl` | real-model results |
