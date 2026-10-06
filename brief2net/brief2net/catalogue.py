"""Operator catalogue: the only Houdini building blocks the builder may use.

Each entry lists a native SOP type, how many inputs it accepts, and the
parameter names the builder is allowed to set.

IMPORTANT — honesty note
------------------------
These names were written from documentation knowledge, NOT harvested from a
running Houdini. Entries marked confidence="medium" are the ones most likely
to differ between Houdini versions. Run `houdini/harvest_catalogue.py` inside
Houdini to replace this file with ground truth before trusting any result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class OpDef:
    type: str
    label: str
    max_inputs: int
    parms: Dict[str, str] = field(default_factory=dict)  # name -> "float"|"int"|"string"|"menu"|"toggle"
    confidence: str = "high"
    purpose: str = ""


def _xyz(prefix: str, kind: str = "float") -> Dict[str, str]:
    return {f"{prefix}{a}": kind for a in "xyz"}


CATALOGUE: Dict[str, OpDef] = {
    # --- generators (no inputs) -------------------------------------------
    "grid": OpDef("grid", "Grid", 0,
                  {"sizex": "float", "sizey": "float", "rows": "int", "cols": "int",
                   "orient": "menu", **_xyz("t")},
                  purpose="Flat ground plane"),
    "box": OpDef("box", "Box", 1,
                 {**_xyz("size"), "scale": "float", **_xyz("t"), "type": "menu"},
                 purpose="Box primitive"),
    "sphere": OpDef("sphere", "Sphere", 1,
                    {**_xyz("rad"), "type": "menu", "freq": "int", **_xyz("t")},
                    purpose="Sphere primitive"),
    "tube": OpDef("tube", "Tube", 1,
                  {"rad1": "float", "rad2": "float", "height": "float",
                   "rows": "int", "cols": "int", "cap": "toggle", **_xyz("t")},
                  purpose="Cylinder / cone"),
    "line": OpDef("line", "Line", 0,
                  {"dist": "float", "points": "int", **_xyz("dir")},
                  purpose="Straight polyline"),
    # --- modifiers --------------------------------------------------------
    "xform": OpDef("xform", "Transform", 1,
                   {**_xyz("t"), **_xyz("r"), **_xyz("s"), "scale": "float"},
                   purpose="Move / rotate / scale"),
    "mountain::2.0": OpDef("mountain::2.0", "Mountain", 1,
                           {"height": "float", "elementsize": "float"},
                           confidence="medium", purpose="Fractal noise displacement"),
    "subdivide": OpDef("subdivide", "Subdivide", 2, {"iterations": "int"},
                       purpose="Smooth / add resolution"),
    "polyextrude::2.0": OpDef("polyextrude::2.0", "PolyExtrude", 2,
                              {"dist": "float", "inset": "float"},
                              confidence="medium", purpose="Extrude faces"),
    "color": OpDef("color", "Color", 1, {"colorr": "float", "colorg": "float",
                                         "colorb": "float", "class": "menu"},
                   purpose="Assign colour attribute"),
    "scatter::2.0": OpDef("scatter::2.0", "Scatter", 1,
                          {"npts": "int", "seed": "float", "relaxpoints": "toggle"},
                          confidence="medium", purpose="Scatter points on a surface"),
    "attribwrangle": OpDef("attribwrangle", "Attribute Wrangle", 4,
                           {"snippet": "string", "class": "menu"},
                           purpose="Small VEX snippet (kept short and readable)"),
    "copyxform": OpDef("copyxform", "Copy and Transform", 1,
                       {"ncy": "int", **_xyz("t"), **_xyz("r"), **_xyz("s"), "scale": "float"},
                       purpose="Repeat geometry with an incremental transform"),
    "copytopoints::2.0": OpDef("copytopoints::2.0", "Copy to Points", 2,
                               {"pack": "toggle"}, confidence="medium",
                               purpose="Instance geometry onto points"),
    # --- structure --------------------------------------------------------
    "merge": OpDef("merge", "Merge", 9999, {}, purpose="Combine streams"),
    "null": OpDef("null", "Null", 1, {}, purpose="Named output marker"),
}


def _apply_harvest() -> None:
    """If harvest_catalogue.py has been run in Houdini, trust its results."""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "catalogue_harvested.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    for key, real in data.items():
        op = CATALOGUE.get(key)
        if op is None:
            continue
        known = {p: k for p, k in op.parms.items() if p in real["parms"]}
        CATALOGUE[key] = OpDef(op.type, op.label, real["max_inputs"], known,
                               confidence="verified", purpose=op.purpose)


_apply_harvest()


def get(op_type: str) -> Optional[OpDef]:
    return CATALOGUE.get(op_type)
