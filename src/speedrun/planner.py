"""Fast Downward plan files.

This module currently holds only the ``Plan`` dataclass and ``parse_plan``,
which the compiler (Task 4.2) needs. The Fast Downward runner (``run_planner``
and the ``PlannerError`` hierarchy) is added by Task 4.1.
"""

import re
from dataclasses import dataclass

# FD writes "; cost = N (general cost)", or "(unit cost)" on unit-cost tasks.
_COST_RE = re.compile(r";\s*cost\s*=\s*(\d+)\b", re.IGNORECASE)
_ACTION_RE = re.compile(r"\(\s*([^()\s][^()]*?)\s*\)")


@dataclass
class Plan:
    actions: list[tuple[str, ...]]  # lower-cased action name followed by its args
    cost: int


def parse_plan(text: str) -> Plan:
    """Parse FD plan text: one ``(name arg ...)`` per line, plus an optional cost trailer.

    Blank lines and ``;`` comments are ignored, except ``; cost = N (...)``,
    which sets ``cost``. Without a trailer, ``cost`` is the number of actions.
    Any other line raises ``ValueError``.
    """
    actions: list[tuple[str, ...]] = []
    cost: int | None = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(";"):
            m = _COST_RE.match(line)
            if m:
                cost = int(m.group(1))
            continue
        m = _ACTION_RE.fullmatch(line)
        if not m:
            raise ValueError(f"plan line {lineno}: not a ground action: {raw!r}")
        actions.append(tuple(m.group(1).lower().split()))
    return Plan(actions=actions, cost=len(actions) if cost is None else cost)
