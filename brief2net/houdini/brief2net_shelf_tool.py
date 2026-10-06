"""Houdini entry point — paste into a shelf tool's Script tab (Python).

1. Right-click a shelf > New Tool... ; Name: brief2net ; Script language: Python
2. Paste this whole file into the Script tab, set BRIEF2NET_HOME below, Accept.
3. Click the tool, type a brief, press Build.
"""
import sys

import hou

BRIEF2NET_HOME = r"C:/path/to/brief2net"      # <-- folder that contains main.py
if BRIEF2NET_HOME not in sys.path:
    sys.path.insert(0, BRIEF2NET_HOME)

from brief2net.codegen import generate          # noqa: E402
from brief2net.drafter import NoMatchingRecipe, RuleDrafter  # noqa: E402
from brief2net.validator import validate        # noqa: E402

button, brief = hou.ui.readInput(
    "Describe the procedural asset you want drafted:\n"
    "(e.g. 'a dense field of rocks on hilly terrain, 500 rocks')",
    buttons=("Build", "Cancel"), title="brief2net — Network Builder")

if button == 0 and brief.strip():
    try:
        draft = RuleDrafter().draft(brief)
    except NoMatchingRecipe as e:
        hou.ui.displayMessage(str(e), title="brief2net")
    else:
        report = validate(draft.spec)
        if not report.ok:
            hou.ui.displayMessage(str(report), title="brief2net — draft rejected",
                                  severity=hou.severityType.Error)
        else:
            script = generate(draft.spec)
            exec(compile(script, "<brief2net build>", "exec"), {"__name__": "__brief2net__"})
            hou.ui.displayMessage(
                "Built. Please check these assumptions:\n\n- " + "\n- ".join(draft.assumptions)
                + ("\n\nWarnings:\n- " + "\n- ".join(report.warnings) if report.warnings else ""),
                title="brief2net — done")
