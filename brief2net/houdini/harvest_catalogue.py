"""Run INSIDE Houdini (Python Shell) to replace guessed parm names with real ones.

    exec(open(r'C:/path/to/brief2net/houdini/harvest_catalogue.py').read())

It creates each catalogue operator in a throwaway container, records its real
parameter names and input count, writes brief2net/catalogue_harvested.json,
prints every mismatch, and deletes the throwaway container. Once the JSON
exists, brief2net uses it automatically and marks those operators verified.
"""
import json
import os
import sys

import hou

HOME = os.path.dirname(os.path.dirname(os.path.abspath(
    globals().get("__file__", r"C:/path/to/brief2net/houdini/harvest_catalogue.py"))))
sys.path.insert(0, HOME)
from brief2net.catalogue import CATALOGUE  # noqa: E402

tmp = hou.node("/obj").createNode("geo", "brief2net_harvest_tmp")
out, problems = {}, []
try:
    for key, op in CATALOGUE.items():
        try:
            n = tmp.createNode(key)
        except hou.OperationFailed:
            problems.append(f"{key}: operator type not found in this Houdini")
            continue
        real = {p.name() for p in n.parms()}
        missing = sorted(set(op.parms) - real)
        if missing:
            problems.append(f"{key}: catalogue parms not found: {missing}")
        out[key] = {"max_inputs": n.type().maxNumInputs(), "parms": sorted(real),
                    "houdini": hou.applicationVersionString()}
        n.destroy()
finally:
    tmp.destroy()

path = os.path.join(HOME, "brief2net", "catalogue_harvested.json")
with open(path, "w") as f:
    json.dump(out, f, indent=1)
print("Wrote", path)
print("\n".join(problems) if problems else "All catalogue entries match this Houdini.")
