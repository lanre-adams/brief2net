"""A small stand-in for Houdini's `hou` module, used to dry-run build scripts.

It is strict where real Houdini is strict (unknown operator types and
parameter names fail) and records everything the script does, so we can test
the pipeline on any machine. It does NOT cook geometry: it proves the script
would build the intended network, not that the result looks good.
"""
from __future__ import annotations

import re
import sys
import types
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from .catalogue import CATALOGUE


class OperationFailed(Exception):
    pass


class _Parm:
    def __init__(self, node: "_Node", name: str):
        self.node, self._name = node, name
        self.value: Any = 0
        self.expression: Optional[str] = None

    def name(self):
        return self._name

    def set(self, v):
        self.value, self.expression = v, None

    def setExpression(self, expr, language=None):
        self.expression = expr

    def eval(self):
        if self.expression is None:
            return self.value
        return _eval_hscript(self.expression, self.node)


class _Node:
    def __init__(self, parent: Optional["_Node"], type_name: str, name: str):
        self.parent, self._type, self._name = parent, type_name, name
        self._children: Dict[str, _Node] = {}
        self._inputs: Dict[int, _Node] = {}
        self._parms: Dict[str, _Parm] = {}
        self.comment = ""
        self.display = self.render = False
        self._ptg = ParmTemplateGroup()
        self.sticky_notes: List[str] = []
        op = CATALOGUE.get(type_name)
        if op:
            for p in op.parms:
                self._parms[p] = _Parm(self, p)

    # -- identity --
    def name(self):
        return self._name

    def path(self):
        return (self.parent.path().rstrip("/") + "/" + self._name) if self.parent else "/" + self._name

    def type_name(self):
        return self._type

    # -- hierarchy --
    def createNode(self, type_name: str, node_name: Optional[str] = None):
        if type_name != "geo" and type_name not in CATALOGUE:
            raise OperationFailed(f"Invalid node type name: {type_name}")
        node_name = node_name or f"{type_name.split('::')[0]}1"
        if node_name in self._children:
            raise OperationFailed(f"Node name already in use: {node_name}")
        n = _Node(self, type_name, node_name)
        self._children[node_name] = n
        return n

    def node(self, rel: str):
        return self._children.get(rel)

    def children(self):
        return tuple(self._children.values())

    def destroy(self):
        if self.parent:
            del self.parent._children[self._name]

    # -- parms --
    def parm(self, name: str):
        return self._parms.get(name)          # None for unknown, like real hou

    def parmTemplateGroup(self):
        return self._ptg

    def setParmTemplateGroup(self, ptg: "ParmTemplateGroup"):
        self._ptg = ptg
        for t in ptg.all_templates():
            p = _Parm(self, t.name)
            p.value = t.default_value[0]
            self._parms[t.name] = p

    # -- wiring / flags / misc --
    def setInput(self, idx: int, src: "_Node", out_idx: int = 0):
        op = CATALOGUE.get(self._type)
        if op and idx >= op.max_inputs:
            raise OperationFailed(f"{self.path()}: input {idx} out of range")
        self._inputs[idx] = src

    def inputs(self):
        return tuple(self._inputs[i] for i in sorted(self._inputs))

    def setDisplayFlag(self, on):
        self.display = on

    def setRenderFlag(self, on):
        self.render = on

    def setComment(self, text):
        self.comment = text

    def layoutChildren(self):
        pass

    def createStickyNote(self):
        node = self

        class _Sticky:
            def setText(self, t):
                node.sticky_notes.append(t)
        return _Sticky()


class _Template:
    def __init__(self, name, label, num_components=1, default_value=(0,), min=0, max=1,
                 help="", **kw):
        self.name, self.label, self.default_value = name, label, default_value
        self.min, self.max, self.help = min, max, help


class FloatParmTemplate(_Template):
    kind = "float"


class IntParmTemplate(_Template):
    kind = "int"


class FolderParmTemplate:
    def __init__(self, name, label, **kw):
        self.name, self.label, self.children = name, label, []

    def addParmTemplate(self, t):
        self.children.append(t)


class ParmTemplateGroup:
    def __init__(self):
        self.entries: List[Any] = []

    def append(self, t):
        self.entries.append(t)

    def all_templates(self):
        for e in self.entries:
            yield from (e.children if isinstance(e, FolderParmTemplate) else [e])


_CH = re.compile(r'ch\(\s*"\.\./([A-Za-z_]\w*)"\s*\)')


def _eval_hscript(expr: str, node: _Node):
    """Evaluate the tiny HScript subset the generator emits: ch("../x") and arithmetic."""
    container = node.parent

    def sub(m):
        p = container.parm(m.group(1))
        if p is None:
            raise OperationFailed(f"{node.path()}: ch(\"../{m.group(1)}\") points at nothing")
        return repr(float(p.eval()))

    py = _CH.sub(sub, expr)
    if not re.fullmatch(r"[0-9eE\.\+\-\*/\(\)\s]+", py):
        raise OperationFailed(f"Unsupported expression in mock: {expr}")
    return eval(py, {"__builtins__": {}}, {})


class _Undos:
    @contextmanager
    def group(self, label):
        yield


class _ExprLang:
    Hscript = "hscript"
    Python = "python"


def make_module():
    """Return (module, root) — a fresh fake `hou` with an empty /obj."""
    root = _Node(None, "root", "")
    obj = _Node(root, "obj", "obj")
    root._children["obj"] = obj

    m = types.ModuleType("hou")

    def node(path: str):
        cur = root
        for part in [p for p in path.split("/") if p]:
            cur = cur.node(part)
            if cur is None:
                return None
        return cur

    m.node = node
    m.OperationFailed = OperationFailed
    m.FloatParmTemplate, m.IntParmTemplate = FloatParmTemplate, IntParmTemplate
    m.FolderParmTemplate = FolderParmTemplate
    m.undos = _Undos()
    m.exprLanguage = _ExprLang
    return m, root


def dry_run(script: str):
    """Execute a generated build script against the mock. Returns the geo node."""
    m, root = make_module()
    saved = sys.modules.get("hou")
    sys.modules["hou"] = m
    try:
        ns: Dict[str, Any] = {"__name__": "__brief2net_dryrun__"}
        exec(compile(script, "<build script>", "exec"), ns)
        return ns["result"]
    finally:
        if saved is None:
            sys.modules.pop("hou", None)
        else:
            sys.modules["hou"] = saved
