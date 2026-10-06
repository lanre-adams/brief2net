"""The typed intermediate representation (IR) between the AI and Houdini.

Nothing the AI produces goes straight into Houdini. It must first become a
NetworkSpec, which the validator can check line by line. This keeps the AI's
output inspectable and makes failures loud instead of silent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class NodeSpec:
    name: str                      # unique node name inside the network
    type: str                      # native Houdini SOP type, e.g. "grid"
    parms: Dict[str, Any] = field(default_factory=dict)   # literal values
    exprs: Dict[str, str] = field(default_factory=dict)   # HScript expressions
    note: str = ""                 # why the drafter put this node here


@dataclass
class Connection:
    src: str                       # upstream node name
    dst: str                       # downstream node name
    dst_input: int = 0             # which input on the downstream node


@dataclass
class Control:
    """An artist-facing control promoted to the top of the network."""
    name: str                      # parm name, e.g. "rock_count"
    label: str                     # what the artist sees, e.g. "Rock Count"
    kind: str                      # "float" | "int"
    default: float
    min: float
    max: float
    drives: List[str] = field(default_factory=list)  # "node.parm" targets
    help: str = ""


@dataclass
class NetworkSpec:
    name: str
    recipe: str
    brief: str
    nodes: List[NodeSpec] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    controls: List[Control] = field(default_factory=list)
    output: str = "OUT"
    assumptions: List[str] = field(default_factory=list)

    # -- helpers -----------------------------------------------------------
    def node(self, name: str) -> Optional[NodeSpec]:
        return next((n for n in self.nodes if n.name == name), None)

    def control(self, name: str) -> Optional[Control]:
        return next((c for c in self.controls if c.name == name), None)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NetworkSpec":
        return cls(
            name=d["name"], recipe=d.get("recipe", "custom"), brief=d.get("brief", ""),
            nodes=[NodeSpec(**n) for n in d.get("nodes", [])],
            connections=[Connection(**c) for c in d.get("connections", [])],
            controls=[Control(**c) for c in d.get("controls", [])],
            output=d.get("output", "OUT"),
            assumptions=list(d.get("assumptions", [])),
        )

    @classmethod
    def from_json(cls, text: str) -> "NetworkSpec":
        return cls.from_dict(json.loads(text))
