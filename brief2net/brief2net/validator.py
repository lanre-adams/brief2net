"""Validator: the gate between AI output and Houdini.

Every check here exists because a drafted network can be wrong in a way that
Houdini would either reject at build time or — worse — accept silently.
Errors block the build. Warnings are shown to the artist but do not block.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

from .catalogue import CATALOGUE
from .spec import NetworkSpec

NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Parameter names a Houdini Geometry object already owns; a control with one of
# these names would collide when the build script adds the Artist Controls tab.
RESERVED = {"tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "px", "py", "pz",
            "prx", "pry", "prz", "scale", "xOrd", "rOrd", "display", "tdisplay",
            "keeppos", "childcomp", "lookatpath", "lookup", "pathobjpath", "roll",
            "pos", "up", "bank", "categories", "caching", "picking"}
CH_RE = re.compile(r'ch\(\s*"\.\./([A-Za-z_][A-Za-z0-9_]*)"\s*\)')


@dataclass
class Report:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def __str__(self) -> str:
        lines = [f"Validation: {'PASS' if self.ok else 'FAIL'} "
                 f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"]
        lines += [f"  ERROR   {e}" for e in self.errors]
        lines += [f"  warning {w}" for w in self.warnings]
        return "\n".join(lines)


def validate(spec: NetworkSpec) -> Report:
    r = Report()
    names = [n.name for n in spec.nodes]

    if not spec.nodes:
        r.errors.append("Network has no nodes.")
        return r

    # --- nodes ---------------------------------------------------------------
    seen: Set[str] = set()
    for n in spec.nodes:
        if not NAME_RE.match(n.name):
            r.errors.append(f"Node name '{n.name}' is not a valid Houdini node name.")
        if n.name in seen:
            r.errors.append(f"Duplicate node name '{n.name}'.")
        seen.add(n.name)

        op = CATALOGUE.get(n.type)
        if op is None:
            r.errors.append(f"{n.name}: operator type '{n.type}' is not in the catalogue.")
            continue
        if op.confidence == "medium":
            r.warnings.append(f"{n.name}: '{n.type}' parm names are {op.confidence}-confidence "
                              "until the catalogue is harvested from Houdini.")
        both = set(n.parms) & set(n.exprs)
        for p in both:
            r.errors.append(f"{n.name}.{p}: set both as a value and an expression.")
        for p, val in list(n.parms.items()) + list(n.exprs.items()):
            if p not in op.parms:
                r.errors.append(f"{n.name}: '{op.type}' has no parameter '{p}'.")
                continue
            if p in n.parms:
                kind = op.parms[p]
                if kind in ("float", "int", "menu", "toggle") and not isinstance(val, (int, float)):
                    r.errors.append(f"{n.name}.{p}: expected a number, got {val!r}.")
                if kind == "string" and not isinstance(val, str):
                    r.errors.append(f"{n.name}.{p}: expected text, got {val!r}.")

    # --- connections & graph shape --------------------------------------------
    slots: Set[tuple] = set()
    edges: Dict[str, List[str]] = {n: [] for n in names}
    for c in spec.connections:
        if c.src not in edges or c.dst not in edges:
            r.errors.append(f"Connection {c.src} -> {c.dst}: unknown node.")
            continue
        op = CATALOGUE.get(spec.node(c.dst).type)
        if op and c.dst_input >= op.max_inputs:
            r.errors.append(f"Connection {c.src} -> {c.dst}[{c.dst_input}]: "
                            f"'{op.type}' accepts {op.max_inputs} input(s).")
        if (c.dst, c.dst_input) in slots:
            r.errors.append(f"{c.dst} input {c.dst_input} is wired twice.")
        slots.add((c.dst, c.dst_input))
        edges[c.src].append(c.dst)

    if _has_cycle(edges):
        r.errors.append("The network contains a loop; SOP networks must flow one way.")

    if spec.output not in edges:
        r.errors.append(f"Output node '{spec.output}' does not exist.")
    else:
        feeds = _reaches(edges, spec.output)
        for n in names:
            if n not in feeds:
                r.warnings.append(f"{n}: does not feed the output '{spec.output}' (dead branch).")

    # --- controls --------------------------------------------------------------
    all_text = " ".join([str(v) for n in spec.nodes for v in n.exprs.values()] +
                        [str(v) for n in spec.nodes for v in n.parms.values() if isinstance(v, str)])
    referenced = set(CH_RE.findall(all_text))
    ctrl_names = set()
    for c in spec.controls:
        if not NAME_RE.match(c.name):
            r.errors.append(f"Control name '{c.name}' is not a valid parameter name.")
        if c.name in RESERVED:
            r.errors.append(f"Control '{c.name}' clashes with a built-in Geometry object parameter.")
        if c.name in ctrl_names:
            r.errors.append(f"Duplicate control '{c.name}'.")
        ctrl_names.add(c.name)
        if c.kind not in ("float", "int"):
            r.errors.append(f"Control '{c.name}': kind must be float or int.")
        if not (c.min <= c.default <= c.max):
            r.errors.append(f"Control '{c.name}': default {c.default} outside [{c.min}, {c.max}].")
        if c.name not in referenced:
            r.errors.append(f"Control '{c.name}' is not used by any node (it would do nothing).")
        for target in c.drives:
            node_name, _, parm = target.partition(".")
            node = spec.node(node_name)
            if node is None:
                r.errors.append(f"Control '{c.name}' drives unknown node '{node_name}'.")
            elif f'"../{c.name}"' not in node.exprs.get(parm, ""):
                r.errors.append(f"Control '{c.name}' claims to drive {target}, "
                                "but that parameter does not reference it.")

    for ref in referenced - ctrl_names:
        r.errors.append(f"Expression references ch(\"../{ref}\") but no such control exists.")

    if not spec.controls:
        r.warnings.append("No artist controls were exposed; the network will be harder to edit.")
    return r


def _has_cycle(edges: Dict[str, List[str]]) -> bool:
    state: Dict[str, int] = {}

    def visit(n: str) -> bool:
        state[n] = 1
        for m in edges.get(n, []):
            if state.get(m) == 1 or (state.get(m) is None and visit(m)):
                return True
        state[n] = 2
        return False

    return any(state.get(n) is None and visit(n) for n in edges)


def _reaches(edges: Dict[str, List[str]], target: str) -> Set[str]:
    rev: Dict[str, List[str]] = {n: [] for n in edges}
    for s, ds in edges.items():
        for d in ds:
            rev[d].append(s)
    out, stack = {target}, [target]
    while stack:
        for p in rev[stack.pop()]:
            if p not in out:
                out.add(p)
                stack.append(p)
    return out
