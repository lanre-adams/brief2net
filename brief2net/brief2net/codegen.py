"""Code generator: validated NetworkSpec -> standalone Houdini Python build script.

The emitted script depends only on Houdini's own `hou` module, so an artist can
read it, keep it, version it and run it without installing brief2net.
It is wrapped in one undo group, so Ctrl+Z removes the whole build.
"""
from __future__ import annotations

import datetime as _dt
import textwrap

from . import __version__
from .spec import NetworkSpec
from .validator import validate


class SpecInvalid(ValueError):
    pass


def generate(spec: NetworkSpec, parent: str = "/obj") -> str:
    report = validate(spec)
    if not report.ok:
        raise SpecInvalid(str(report))

    L = []
    w = L.append
    header_brief = "\n".join("#   " + line for line in textwrap.wrap(spec.brief or "(none)", 76))
    w("# " + "=" * 76)
    w(f"# brief2net {__version__} — generated Houdini build script")
    w(f"# Generated: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}   Recipe: {spec.recipe}")
    w("# Brief:")
    w(header_brief)
    w("# Assumptions made by the drafter (check these!):")
    for a in spec.assumptions or ["(none recorded)"]:
        for i, line in enumerate(textwrap.wrap(a, 74)):
            w(("#   - " if i == 0 else "#     ") + line)
    w("#")
    w("# HOW TO RUN: Houdini > Windows > Python Shell, then:")
    w("#   exec(open(r'/path/to/this_file.py').read())")
    w("# Everything it builds is a normal, editable Houdini node. Ctrl+Z undoes it.")
    w("# " + "=" * 76)
    w("import hou")
    w("")
    w("")
    w(f"def build(parent_path={parent!r}, name={spec.name!r}):")
    w('    """Build the network and return the geometry container node."""')
    w("    parent = hou.node(parent_path)")
    w("    if parent is None:")
    w("        raise RuntimeError('Parent network %s not found' % parent_path)")
    w("    base, i = name, 1")
    w("    while parent.node(name) is not None:   # never overwrite existing work")
    w("        i += 1")
    w("        name = '%s_%d' % (base, i)")
    w("")
    w("    with hou.undos.group('brief2net: build ' + name):")
    w("        geo = parent.createNode('geo', name)")
    w("        for child in geo.children():        # start from an empty container")
    w("            child.destroy()")
    w("")
    w("        # ---- 1. Artist controls (top of the container's parameter pane) ----")
    w("        ptg = geo.parmTemplateGroup()")
    w("        folder = hou.FolderParmTemplate('artist_controls', 'Artist Controls')")
    for c in spec.controls:
        cls = "hou.FloatParmTemplate" if c.kind == "float" else "hou.IntParmTemplate"
        default = float(c.default) if c.kind == "float" else int(c.default)
        lo = float(c.min) if c.kind == "float" else int(c.min)
        hi = float(c.max) if c.kind == "float" else int(c.max)
        w(f"        folder.addParmTemplate({cls}({c.name!r}, {c.label!r}, 1, "
          f"default_value=({default!r},), min={lo!r}, max={hi!r}, help={c.help!r}))")
    w("        ptg.append(folder)")
    w("        geo.setParmTemplateGroup(ptg)")
    w("")
    w("        # ---- 2. Nodes (all native operators) ----")
    w("        n = {}")
    for node in spec.nodes:
        w(f"        n[{node.name!r}] = geo.createNode({node.type!r}, {node.name!r})")
        if node.note:
            w(f"        n[{node.name!r}].setComment({node.note!r})")
        for p, v in node.parms.items():
            w(f"        n[{node.name!r}].parm({p!r}).set({v!r})")
        for p, e in node.exprs.items():
            w(f"        n[{node.name!r}].parm({p!r}).setExpression({e!r}, hou.exprLanguage.Hscript)")
    w("")
    w("        # ---- 3. Wiring ----")
    for c in spec.connections:
        w(f"        n[{c.dst!r}].setInput({c.dst_input}, n[{c.src!r}], 0)")
    w("")
    w("        # ---- 4. Flags, layout and a note for the next person ----")
    w(f"        n[{spec.output!r}].setDisplayFlag(True)")
    w(f"        n[{spec.output!r}].setRenderFlag(True)")
    w("        geo.layoutChildren()")
    note = (f"Built by brief2net from the brief:\n{spec.brief}\n\n"
            "Edit anything. Main knobs: container > Artist Controls tab.")
    w("        sticky = geo.createStickyNote()")
    w(f"        sticky.setText({note!r})")
    w("    return geo")
    w("")
    w("")
    w("result = build()")
    w("print('brief2net: built', result.path())")
    return "\n".join(L) + "\n"
