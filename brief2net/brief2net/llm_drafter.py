"""Optional LLM drafter: asks a language model to fill a NetworkSpec as JSON.

Status: written against the public Anthropic Messages API but NOT exercised in
this prototype's tests (no network or key in the build environment). It is
here to show where the generative step plugs in. Whatever the model returns
is validated; on failure the validator's errors are sent back for one repair
attempt, and if it still fails we stop rather than build something broken.

Enable:  export ANTHROPIC_API_KEY=...   then   python main.py build "..." --llm
"""
from __future__ import annotations

import json
import os
import urllib.request

from .catalogue import CATALOGUE
from .drafter import Draft
from .spec import NetworkSpec
from .validator import validate

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("BRIEF2NET_MODEL", "claude-sonnet-5-5")

SYSTEM = """You draft Houdini SOP networks for an experienced technical artist.
Return ONLY a JSON object with keys: name, recipe ("llm"), brief, nodes, connections,
controls, output, assumptions.
- nodes: [{name, type, parms:{}, exprs:{}, note}] — type MUST be one of the catalogue
  types below and every parm name MUST be listed for that type.
- connections: [{src, dst, dst_input}]
- controls: [{name, label, kind:"float"|"int", default, min, max, drives:["node.parm"], help}]
  Each control must be referenced as ch("../<name>") in the exprs of the parms it drives.
- The output node is a "null" called OUT.
- List every guess you made in assumptions. Prefer few nodes and meaningful controls.
Catalogue:
"""


def _catalogue_text() -> str:
    return "\n".join(f"- {o.type}: inputs<={o.max_inputs}; parms={sorted(o.parms)}"
                     for o in CATALOGUE.values())


def _call(messages) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set; use the default rule-based drafter.")
    body = json.dumps({"model": MODEL, "max_tokens": 4000,
                       "system": SYSTEM + _catalogue_text(), "messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return "".join(b.get("text", "") for b in data.get("content", []))


def _parse(text: str) -> NetworkSpec:
    start, end = text.find("{"), text.rfind("}")
    return NetworkSpec.from_dict(json.loads(text[start:end + 1]))


class LLMDrafter:
    name = f"LLM ({MODEL})"

    def draft(self, brief: str, recipe: str | None = None) -> Draft:
        messages = [{"role": "user", "content": f"Brief: {brief}"}]
        reply = _call(messages)
        spec = _parse(reply)
        report = validate(spec)
        if not report.ok:   # one repair round, driven by the validator
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": "Fix these validation errors and return the "
                                                     "full JSON again:\n" + "\n".join(report.errors)}]
            spec = _parse(_call(messages))
            report = validate(spec)
            if not report.ok:
                raise ValueError("LLM draft still invalid after repair:\n" + str(report))
        spec.brief = brief
        spec.assumptions.append(f"Drafted by {self.name}; validated.")
        return Draft(spec, {}, "unknown", spec.assumptions)
