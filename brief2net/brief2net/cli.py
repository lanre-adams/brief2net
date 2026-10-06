"""Command-line entry point.

    python main.py                      # friendly interactive mode
    python main.py build "brief" [-o out] [--recipe KEY] [--llm]
    python main.py demo                 # four sample briefs end to end
    python main.py recipes              # what the builder knows how to make
    python main.py check build.py       # dry-run any build script
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap

from . import __version__
from .codegen import generate
from .drafter import NoMatchingRecipe, RuleDrafter
from .evaluate import evaluate
from .mock_hou import dry_run
from .recipes import RECIPES
from .validator import validate

DEMO_BRIEFS = [
    "A dense field of jagged rocks scattered across hilly terrain, about 800 rocks, 150 metres wide.",
    "A tall twisting tower, 30 floors, twisting 3 degrees per floor.",
    "A low wooden fence with 20 posts along a path.",
    "A large craggy rust asteroid for a space shot.",
]


def _hr(title: str = "") -> None:
    print("\n" + ("── " + title + " ").ljust(72, "─"))


def build(brief: str, out_dir: str, recipe: str | None = None, use_llm: bool = False,
          quiet: bool = False) -> dict:
    if use_llm:
        from .llm_drafter import LLMDrafter
        drafter = LLMDrafter()
    else:
        drafter = RuleDrafter()

    draft = drafter.draft(brief, recipe)
    spec = draft.spec
    report = validate(spec)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, spec.name)

    with open(base + ".spec.json", "w") as f:
        f.write(spec.to_json())

    if not quiet:
        _hr("1. Brief")
        print(textwrap.fill(brief, 72))
        _hr(f"2. Draft ({drafter.name})")
        print(f"Recipe: {RECIPES[spec.recipe].title if spec.recipe in RECIPES else spec.recipe}"
              f"   confidence: {draft.confidence}")
        for a in spec.assumptions:
            print(textwrap.fill(a, 72, initial_indent="  • ", subsequent_indent="    "))
        _hr("3. Check")
        print(report)

    if not report.ok:
        print("\nStopped: the draft did not pass validation, so no build script was written.")
        return {"ok": False, "report": report}

    script = generate(spec)
    script_path = base + "_build.py"
    with open(script_path, "w") as f:
        f.write(script)

    ev = evaluate(spec)
    from .preview import render
    png = render(spec, base + "_preview.png")

    md = [f"# {spec.name} — brief2net report", "", f"**Brief:** {brief}", "",
          "## Assumptions", *[f"- {a}" for a in spec.assumptions], "",
          "## Technical evaluation", "| Check | Result |", "|---|---|",
          *[f"| {k} | {v} |" for k, v in ev.rows()], "",
          "## Artist controls", "| Control | Default | Range | Drives |", "|---|---|---|---|",
          *[f"| {c.label} | {c.default:g} | {c.min:g}–{c.max:g} | "
            f"{', '.join(c.drives) or 'read in VEX'} |" for c in spec.controls]]
    with open(base + "_report.md", "w") as f:
        f.write("\n".join(md) + "\n")

    if not quiet:
        _hr("4. Build script + evaluation")
        for k, v in ev.rows():
            print(f"  {k:<52} {v}")
        _hr("5. Files written")
        for p in (base + ".spec.json", script_path, png, base + "_report.md"):
            print("  " + p)
        print("\nNext: open Houdini > Windows > Python Shell and run")
        print(f"  exec(open(r'{os.path.abspath(script_path)}').read())")
    return {"ok": True, "spec": spec, "script": script_path, "preview": png, "eval": ev}


def interactive() -> int:
    print(f"brief2net {__version__} — turns a short art brief into an editable Houdini network.\n")
    print("I currently know how to draft:")
    for r in RECIPES.values():
        print(f"  • {r.title}: {r.summary}")
    print("\nDescribe what you want in one or two sentences (or press Enter for an example).")
    try:
        brief = input("> ").strip()
    except EOFError:
        brief = ""
    if not brief:
        brief = DEMO_BRIEFS[0]
        print(f"Using example: {brief}")
    try:
        build(brief, "output")
    except NoMatchingRecipe as e:
        print("\n" + str(e))
        return 1
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return interactive()

    ap = argparse.ArgumentParser(prog="brief2net", description="Brief -> editable Houdini network.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Draft, check and write a build script for a brief")
    b.add_argument("brief")
    b.add_argument("-o", "--out", default="output")
    b.add_argument("--recipe", choices=sorted(RECIPES))
    b.add_argument("--llm", action="store_true", help="Use the optional LLM drafter")

    d = sub.add_parser("demo", help="Run four sample briefs")
    d.add_argument("-o", "--out", default="output/demo")

    sub.add_parser("recipes", help="List what can be drafted")

    c = sub.add_parser("check", help="Dry-run a build script in mock Houdini")
    c.add_argument("script")

    a = ap.parse_args(argv)
    if a.cmd == "build":
        try:
            return 0 if build(a.brief, a.out, a.recipe, a.llm)["ok"] else 2
        except NoMatchingRecipe as e:
            print(str(e))
            return 1
    if a.cmd == "demo":
        for brief in DEMO_BRIEFS:
            build(brief, a.out)
        return 0
    if a.cmd == "recipes":
        for r in RECIPES.values():
            print(f"{r.key:<20} {r.title} — {r.summary}")
            print(f"{'':<20} controls: {', '.join(r.defaults)}")
        return 0
    if a.cmd == "check":
        with open(a.script) as f:
            geo = dry_run(f.read())
        kids = geo.children()
        print(f"OK: built {geo.path()} with {len(kids)} nodes: " + ", ".join(k.name() for k in kids))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
