"""Technical evaluation of a drafted network (objective 3, technical half).

Measures properties that can be checked without a human in the loop:
does it build, are all operators native, does every artist control actually
change something, and how much of the network is driven by those controls.
The *creative* half of objective 3 (agency, usefulness) needs artists and
studies — see the guide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .catalogue import CATALOGUE
from .codegen import generate
from .mock_hou import dry_run
from .spec import NetworkSpec


@dataclass
class Evaluation:
    builds: bool
    nodes: int
    wires: int
    controls: int
    native_ratio: float
    commented_ratio: float
    linked_parms: int
    set_parms: int
    live_controls: List[str] = field(default_factory=list)
    vex_controls: List[str] = field(default_factory=list)
    dead_controls: List[str] = field(default_factory=list)
    error: str = ""

    @property
    def control_liveness(self) -> float:
        checkable = len(self.live_controls) + len(self.dead_controls)
        return len(self.live_controls) / checkable if checkable else 1.0

    def rows(self) -> List[tuple]:
        return [
            ("Builds in mock Houdini", "yes" if self.builds else f"NO — {self.error}"),
            ("Nodes / wires", f"{self.nodes} / {self.wires}"),
            ("Native operators", f"{self.native_ratio:.0%}"),
            ("Nodes with an explanatory comment", f"{self.commented_ratio:.0%}"),
            ("Artist controls exposed", str(self.controls)),
            ("Parameters linked to controls", f"{self.linked_parms} of {self.linked_parms + self.set_parms} set"),
            ("Controls proven live (perturbation test)",
             f"{len(self.live_controls)}/{len(self.live_controls) + len(self.dead_controls)}"),
            ("Controls read inside VEX (needs real cook to verify)",
             ", ".join(self.vex_controls) or "none"),
        ]


def evaluate(spec: NetworkSpec) -> Evaluation:
    ev = Evaluation(builds=False, nodes=len(spec.nodes), wires=len(spec.connections),
                    controls=len(spec.controls),
                    native_ratio=sum(n.type in CATALOGUE for n in spec.nodes) / max(len(spec.nodes), 1),
                    commented_ratio=sum(bool(n.note) for n in spec.nodes) / max(len(spec.nodes), 1),
                    linked_parms=sum(len(n.exprs) for n in spec.nodes),
                    set_parms=sum(len(n.parms) for n in spec.nodes))
    try:
        geo = dry_run(generate(spec))
    except Exception as e:  # report, don't crash the CLI
        ev.error = f"{type(e).__name__}: {e}"
        return ev
    ev.builds = True

    def snapshot() -> Dict[str, float]:
        return {f"{n.name()}.{p}": n.parm(p).eval()
                for n in geo.children()
                for p, parm in n._parms.items() if parm.expression}

    base = snapshot()
    for c in spec.controls:
        p = geo.parm(c.name)
        old = p.value
        span = (c.max - c.min) or 1
        p.set(old + span * 0.1 if old + span * 0.1 <= c.max else old - span * 0.1)
        changed = [k for k, v in snapshot().items() if v != base[k]]
        p.set(old)
        if changed:
            ev.live_controls.append(c.name)
        elif not c.drives:
            ev.vex_controls.append(c.name)
        else:
            ev.dead_controls.append(c.name)
    return ev
