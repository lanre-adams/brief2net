"""Draws the drafted network as a picture, so it can be inspected before Houdini."""
from __future__ import annotations

from typing import Dict, List

from .catalogue import CATALOGUE
from .spec import NetworkSpec

ROLE_COLOURS = {  # light fills, dark text — readable on paper
    "generator": "#D6E9F8", "modifier": "#FDE7C8", "structure": "#E3E3E3", "output": "#D5F0DA",
}
GENERATORS = {"grid", "box", "sphere", "tube", "line"}
STRUCTURE = {"merge", "copytopoints::2.0", "copyxform"}


def _role(spec: NetworkSpec, node) -> str:
    if node.name == spec.output:
        return "output"
    if node.type in GENERATORS:
        return "generator"
    if node.type in STRUCTURE:
        return "structure"
    return "modifier"


def layers(spec: NetworkSpec) -> Dict[str, int]:
    parents: Dict[str, List[str]] = {n.name: [] for n in spec.nodes}
    for c in spec.connections:
        parents[c.dst].append(c.src)
    depth: Dict[str, int] = {}

    def d(n):
        if n not in depth:
            depth[n] = 0 if not parents[n] else 1 + max(d(p) for p in parents[n])
        return depth[n]

    for n in parents:
        d(n)
    return depth


def render(spec: NetworkSpec, path: str, title: str | None = None) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    depth = layers(spec)
    rows: Dict[int, List[str]] = {}
    for n in spec.nodes:
        rows.setdefault(depth[n.name], []).append(n.name)
    max_d = max(rows)
    width = max(len(v) for v in rows.values())

    fig_w = max(8.5, 2.7 * width + 4.6)
    fig_h = 1.15 * (max_d + 1) + 1.3
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    graph_w = fig_w - 3.4
    gap = 2.5
    parents = {n.name: [] for n in spec.nodes}
    for c in spec.connections:
        parents[c.dst].append(c.src)
    xs: Dict[str, float] = {}
    for d in sorted(rows):
        names = rows[d]
        if d == 0:
            desired = {nm: i * gap for i, nm in enumerate(names)}
        else:
            desired = {nm: (sum(xs[p] for p in parents[nm]) / len(parents[nm])) for nm in names}
        order = sorted(names, key=lambda nm: desired[nm])
        placed = []
        for nm in order:   # keep desired x, but never closer than one box gap
            x = desired[nm] if not placed else max(desired[nm], placed[-1][1] + gap)
            placed.append((nm, x))
        shift = (sum(desired[nm] for nm in names) / len(names)) - \
                (sum(x for _, x in placed) / len(placed))
        for nm, x in placed:
            xs[nm] = x + shift
    lo, hi = min(xs.values()), max(xs.values())
    span = max(hi - lo, 0.001)
    pos = {}
    for nm, x in xs.items():
        px_ = 1.2 + (x - lo) / span * (graph_w - 2.4) if hi > lo else graph_w / 2
        pos[nm] = (px_, fig_h - 1.0 - depth[nm] * 1.15)
    rows = {d: sorted(v, key=lambda nm: pos[nm][0]) for d, v in rows.items()}

    for c in spec.connections:
        (x1, y1), (x2, y2) = pos[c.src], pos[c.dst]
        ax.annotate("", xy=(x2, y2 + 0.24), xytext=(x1, y1 - 0.24),
                    arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.1,
                                    shrinkA=0, shrinkB=0,
                                    connectionstyle=("arc3,rad=0.0" if
                                                     depth[c.dst] - depth[c.src] == 1
                                                     else "arc3,rad=0.25")), zorder=2)
        if c.dst_input:
            ax.text(x2 + 0.05, y2 + 0.32, f"in {c.dst_input}", fontsize=6.5, color="#777777")

    driven = {t.split(".")[0] for c in spec.controls for t in c.drives}
    for n in spec.nodes:
        x, y = pos[n.name]
        role = _role(spec, n)
        edge = "#B5651D" if n.name in driven else "#666666"
        ax.add_patch(FancyBboxPatch((x - 1.05, y - 0.24), 2.1, 0.48,
                                    boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc=ROLE_COLOURS[role], ec=edge,
                                    lw=1.8 if n.name in driven else 0.9, zorder=3))
        ax.text(x, y + 0.05, n.name, ha="center", va="center", fontsize=8, weight="bold",
                color="#1A1A1A", zorder=4)
        ax.text(x, y - 0.13, CATALOGUE[n.type].label if n.type in CATALOGUE else n.type,
                ha="center", va="center", fontsize=6.5, color="#444444", zorder=4)

    # artist controls panel
    px = fig_w - 3.2
    panel_h = 0.55 + 0.3 * len(spec.controls)
    ax.add_patch(FancyBboxPatch((px, fig_h - 0.45 - panel_h), 3.0, panel_h,
                                boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc="#FFF8EE", ec="#B5651D", lw=1))
    ax.text(px + 0.15, fig_h - 0.75, "Artist Controls", fontsize=9, weight="bold", color="#7A3E00")
    for i, c in enumerate(spec.controls):
        val = int(c.default) if c.kind == "int" else round(c.default, 2)
        ax.text(px + 0.15, fig_h - 1.1 - i * 0.3, f"{c.label}: {val}", fontsize=7.2, color="#222222")

    ax.text(0.15, fig_h - 0.35, title or f"Drafted network — {spec.name}", fontsize=10.5,
            weight="bold", color="#1A1A1A")
    ax.text(0.15, 0.12, "Blue = makes shape   Orange = changes shape   Grey = combines/copies   "
            "Green = output   Bold brown border = driven by an artist control",
            fontsize=6.5, color="#555555")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path
