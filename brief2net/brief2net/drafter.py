"""The drafting step: artist brief -> NetworkSpec.

Two drafters share one interface:

* RuleDrafter (default, offline, deterministic) — scores the brief against the
  recipe library, pulls numbers and adjectives out of the text, and records
  every guess it makes as an explicit *assumption*. It is a transparent
  baseline, not "real AI"; its job is to make the rest of the pipeline testable
  and to give later AI methods something honest to beat.

* LLMDrafter (optional) — asks a large language model to fill the same spec.
  Whatever it returns still goes through the validator; nothing reaches
  Houdini unchecked. See llm_drafter.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .recipes import RECIPES, Recipe
from .spec import NetworkSpec


class NoMatchingRecipe(ValueError):
    """Raised instead of guessing when the brief matches nothing we know."""


@dataclass
class Draft:
    spec: NetworkSpec
    scores: Dict[str, float]
    confidence: str                     # "high" | "medium" | "low"
    assumptions: List[str] = field(default_factory=list)


WORD = re.compile(r"[a-z][a-z\-]*")
NUM_WORD = re.compile(r"(\d+(?:\.\d+)?)\s*(?:x\s*)?([a-z\-]+)?")

COLOURS = {
    "red": (0.7, 0.2, 0.15), "rust": (0.55, 0.3, 0.18), "orange": (0.85, 0.45, 0.1),
    "yellow": (0.85, 0.75, 0.2), "green": (0.25, 0.55, 0.25), "blue": (0.2, 0.35, 0.7),
    "purple": (0.45, 0.25, 0.6), "grey": (0.5, 0.5, 0.5), "gray": (0.5, 0.5, 0.5),
    "white": (0.9, 0.9, 0.9), "black": (0.08, 0.08, 0.08), "brown": (0.4, 0.28, 0.18),
    "sandy": (0.76, 0.66, 0.48), "icy": (0.75, 0.85, 0.95),
}


class RuleDrafter:
    name = "rule-based baseline"

    def score(self, brief: str) -> Dict[str, float]:
        words = WORD.findall(brief.lower())
        return {k: sum(r.keywords.get(w, 0) for w in words) for k, r in RECIPES.items()}

    def draft(self, brief: str, recipe: str | None = None) -> Draft:
        scores = self.score(brief)
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        if recipe:
            if recipe not in RECIPES:
                raise NoMatchingRecipe(f"Unknown recipe '{recipe}'. Known: {', '.join(RECIPES)}")
            chosen, confidence = recipe, "high"
        else:
            (best, s1), (_, s2) = ranked[0], ranked[1]
            if s1 == 0:
                raise NoMatchingRecipe(
                    "The brief does not match any recipe I know, so I will not guess. "
                    f"Known recipes: {', '.join(RECIPES)}. Try naming the subject "
                    "(e.g. 'rocks on a terrain', 'a 20-floor tower', 'a fence', 'an asteroid') "
                    "or pass --recipe.")
            chosen = best
            confidence = "high" if s1 >= 2 * max(s2, 1) else ("medium" if s1 > s2 else "low")

        r = RECIPES[chosen]
        values, notes = self._extract(brief, r)
        spec = r.build(values, brief)
        spec.assumptions = notes + [f"Recipe chosen: '{r.title}' (keyword score {scores[chosen]:g}; "
                                    f"confidence {confidence})."]
        return Draft(spec, scores, confidence, spec.assumptions)

    # ------------------------------------------------------------------
    def _extract(self, brief: str, r: Recipe) -> Tuple[Dict[str, float], List[str]]:
        text = brief.lower()
        values = dict(r.defaults)
        set_by_brief = set()
        touched = set()
        notes: List[str] = []

        # 1. "<number> <noun>" pairs, e.g. "500 rocks", "30 floors"
        for num, unit in NUM_WORD.findall(text):
            if not unit:
                continue
            for ctrl, nouns in r.number_hints.items():
                if unit in nouns and ctrl not in set_by_brief:
                    values[ctrl] = float(num)
                    set_by_brief.add(ctrl)
                    touched.add(ctrl)
                    notes.append(f"Read '{num} {unit}' as {ctrl} = {num}.")
                    break

        # 2. adjectives that nudge defaults (each nudge is recorded)
        def nudge(ctrl: str, factor: float, word: str):
            if ctrl in values and ctrl not in set_by_brief:
                values[ctrl] = round(values[ctrl] * factor, 3)
                touched.add(ctrl)
                notes.append(f"'{word}' -> {ctrl} x{factor} (now {values[ctrl]:g}).")

        for word, ctrl, f in [
            ("dense", "instance_count", 2.5), ("sparse", "instance_count", 0.4),
            ("hilly", "terrain_height", 2.0), ("mountainous", "terrain_height", 3.0),
            ("flat", "terrain_height", 0.2), ("huge", "max_scale", 2.5),
            ("tiny", "max_scale", 0.4), ("jagged", "piece_roughness", 2.0),
            ("smooth", "piece_roughness", 0.3), ("tall", "floor_count", 2.0),
            ("short", "post_height", 0.7), ("low", "post_height", 0.6),
            ("high", "post_height", 1.5), ("rough", "roughness", 2.0),
            ("craggy", "roughness", 2.5), ("smooth", "roughness", 0.3),
            ("large", "radius", 2.5), ("small", "radius", 0.4),
        ]:
            if re.search(rf"\b{word}\b", text):
                nudge(ctrl, f, word)

        if "twist" in values and re.search(r"\btwist(ing|ed|s)?\b", text) and "twist" not in set_by_brief:
            values["twist"] = 4.0
            touched.add("twist")
            notes.append("'twist' mentioned without an angle -> assumed 4 degrees per floor.")

        if "tint_r" in values:
            for name, rgb in COLOURS.items():
                if re.search(rf"\b{name}\b", text):
                    values["tint_r"], values["tint_g"], values["tint_b"] = rgb
                    touched.update({"tint_r", "tint_g", "tint_b"})
                    notes.append(f"Colour word '{name}' -> tint {rgb}.")
                    break

        # integer controls must be integers
        for k in ("instance_count", "floor_count", "post_count", "detail"):
            if k in values:
                values[k] = int(round(values[k]))

        untouched = [k for k in r.defaults if k not in touched]
        if untouched:
            notes.append("Left at recipe defaults (brief did not say): " + ", ".join(untouched) + ".")
        return values, notes
