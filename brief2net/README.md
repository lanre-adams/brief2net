# brief2net

**From an artist's brief to an editable Houdini node network.**

brief2net is a research prototype of an AI-augmented *Network Builder* for technical artists.
You describe a procedural asset in a sentence. brief2net drafts a typed plan, checks it, and writes a
standalone Python script that builds a **native, editable SOP network** in Houdini, with the
meaningful knobs promoted to an **Artist Controls** tab.

It drafts *tools*, not final images. The artist keeps creative direction: every guess the system
makes is written down, and everything it builds is an ordinary Houdini node that can be changed,
rewired or deleted.

> **Status: v0.1.0, early prototype.** Tested end to end against a strict mock of Houdini's `hou`
> module. **Not yet run in a real Houdini session.** See [Limitations](#limitations).

![Pipeline: brief → draft → check → build script → Houdini, with the artist in the loop](docs/images/pipeline.png)

---

## Contents

- [Why](#why)
- [Quick start](#quick-start)
- [Using it in Houdini](#using-it-in-houdini)
- [Example](#example)
- [How it works](#how-it-works)
- [What it can draft today](#what-it-can-draft-today)
- [Evaluation](#evaluation)
- [Repository layout](#repository-layout)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Research context](#research-context)
- [Licence](#licence)

---

## Why

Procedural node-based systems like Houdini give artists transparent, reproducible and fully
editable control. Building those networks takes real expertise and is often repetitive: each new
task means constructing or adapting large graphs of nodes and parameters.

brief2net explores whether AI can help **at the level of tool production**: drafting a sensible
starting network that an experienced technical artist can inspect, modify and extend, rather than
generating a finished scene that cannot be edited.

Three design rules follow from that:

1. **Native only.** Output uses standard Houdini operators. No opaque custom nodes, no hidden state.
2. **Checkable before it runs.** The AI fills a typed plan (`NetworkSpec`), and a validator must
   pass it before any Houdini code is written.
3. **Editable after it runs.** Key values are exposed as artist controls and linked into the
   network with `ch("../name")` expressions, so one knob updates every node that depends on it.

## Quick start

Requires **Python 3.9+**. The only dependency is `matplotlib` (for preview diagrams).

```bash
git clone https://github.com/lanre-adams/brief2net.git
cd brief2net
pip install -r requirements.txt

python main.py                 # guided prompt — type a brief, or press Enter for an example
python main.py demo            # four sample briefs → output/demo/
python -m unittest discover -s tests   # 27 tests
```

No terminal? Double-click `start_here_windows.bat` (Windows) or run `sh start_here_mac_linux.sh`.

### Commands

| Command | What it does |
|---|---|
| `python main.py` | Interactive mode |
| `python main.py build "<brief>" [-o DIR] [--recipe KEY] [--llm]` | Draft, validate and write a build script |
| `python main.py demo [-o DIR]` | Run the four sample briefs |
| `python main.py recipes` | List what can be drafted and each recipe's controls |
| `python main.py check FILE_build.py` | Dry-run any build script in mock Houdini |

Each build writes four files:

| File | Purpose |
|---|---|
| `<name>.spec.json` | The drafted plan. Human-readable; edit and rebuild from it. |
| `<name>_build.py` | Standalone Houdini script. Header lists the brief and every assumption. |
| `<name>_preview.png` | Diagram of the network and its controls, for review before Houdini. |
| `<name>_report.md` | Technical evaluation and a table of artist controls. |

## Using it in Houdini

**Option A — Python Shell.** In Houdini, open *Windows → Python Shell* and run the line
brief2net prints after a build:

```python
exec(open(r'C:/path/to/brief2net/output/stacked_tower_build.py').read())
```

A new Geometry container appears under `/obj`. Select it and open the **Artist Controls** tab.

**Option B — Shelf tool.** Create a new shelf tool, paste in
[`houdini/brief2net_shelf_tool.py`](houdini/brief2net_shelf_tool.py), and set `BRIEF2NET_HOME`.
Clicking it opens a dialog for your brief and builds immediately.

Every build script:

- needs only Houdini's `hou` module (brief2net does not have to be installed to run it);
- never overwrites existing work (it picks a fresh name if one is taken);
- runs inside a single undo group, so **one Ctrl+Z removes the whole build**;
- adds a comment to each node and a sticky note containing the original brief.

> **First run in Houdini:** execute
> [`houdini/harvest_catalogue.py`](houdini/harvest_catalogue.py) once. It checks every operator and
> parameter name against your Houdini version, reports mismatches, and writes
> `brief2net/catalogue_harvested.json`, which brief2net then uses in place of its built-in guesses.

## Example

```text
$ python main.py build "A dense field of jagged rocks scattered across hilly terrain, about 800 rocks, 150 metres wide."

── 2. Draft (rule-based baseline) ───────────────────────────────────────
Recipe: Scatter objects on terrain   confidence: high
  • Read '800 rocks' as instance_count = 800.
  • Read '150 metres' as terrain_size = 150.
  • 'hilly' -> terrain_height x2.0 (now 12).
  • 'jagged' -> piece_roughness x2.0 (now 0.7).
  • Left at recipe defaults (brief did not say): seed, min_scale, max_scale.

── 3. Check ─────────────────────────────────────────────────────────────
Validation: PASS (0 error(s), 4 warning(s))

── 4. Build script + evaluation ─────────────────────────────────────────
  Builds in mock Houdini                               yes
  Native operators                                     100%
  Artist controls exposed                              7
  Controls proven live (perturbation test)             5/5
  Controls read inside VEX (needs real cook to verify) min_scale, max_scale
```

![Drafted network for the rocks-on-terrain brief](docs/images/scatter_on_terrain_preview.png)

A fragment of the generated build script:

```python
folder.addParmTemplate(hou.IntParmTemplate('floor_count', 'Floors', 1,
                       default_value=(30,), min=1, max=200, help=''))
...
n['stack_floors'] = geo.createNode('copyxform', 'stack_floors')
n['stack_floors'].setComment('Repeats the floor upward; Twist rotates each floor')
n['stack_floors'].parm('ncy').setExpression('ch("../floor_count")', hou.exprLanguage.Hscript)
n['stack_floors'].parm('ry').setExpression('ch("../twist")', hou.exprLanguage.Hscript)
```

## How it works

```
brief ──► Drafter ──► NetworkSpec ──► Validator ──► Code generator ──► build script ──► Houdini
          (AI step)    (typed JSON)    (gate)        (hou only)                          (artist edits)
```

| Stage | Module | Notes |
|---|---|---|
| Draft | `drafter.py`, `llm_drafter.py` | Produces a `NetworkSpec` and a list of explicit assumptions. Refuses to guess when nothing matches. |
| Plan | `spec.py` | Nodes, connections, artist controls, output node. Serialises to JSON. |
| Check | `validator.py` | Blocks unknown operator types, unknown parameters, wrong value types, double-wired or out-of-range inputs, loops, missing output, dangling `ch()` references, controls that drive nothing, out-of-range defaults, and control names that clash with built-in object parameters. Warns on dead branches and medium-confidence operators. |
| Generate | `codegen.py` | Refuses invalid specs. Emits a self-contained script. |
| Test | `mock_hou.py` | Strict stand-in for `hou`: unknown types raise, unknown parms return `None` (as in Houdini), simple HScript expressions are evaluated. Does not cook geometry. |
| Measure | `evaluate.py` | See [Evaluation](#evaluation). |
| Preview | `preview.py` | Layered network diagram with the controls panel. |

### Drafters

- **`RuleDrafter` (default).** Offline and deterministic. Scores the brief against each recipe's
  keywords, reads `<number> <noun>` pairs ("30 floors"), applies a small set of adjective nudges
  ("dense", "jagged", "tall", colour words), and records every decision. It is a transparent
  baseline, not machine learning, chosen so the pipeline is testable and later methods have
  something honest to beat.
- **`LLMDrafter` (optional, `--llm`).** Sends the brief and the operator catalogue to a language
  model via the Anthropic Messages API and asks for a `NetworkSpec` as JSON. Validator errors are fed
  back for one repair round; if it still fails, nothing is built. Requires `ANTHROPIC_API_KEY`;
  model is set by `BRIEF2NET_MODEL`. **Written but not yet exercised in tests.**

## What it can draft today

| Recipe | Example brief | Controls |
|---|---|---|
| `scatter_on_terrain` | "800 jagged rocks on hilly terrain" | Terrain Size, Hill Height, Object Count, Random Seed, Min/Max Scale, Roughness |
| `stacked_tower` | "a 30-floor tower twisting 3 degrees per floor" | Floors, Floor Height, Floor Width, Floor Depth, Twist per Floor |
| `fence` | "a low fence with 20 posts" | Posts, Post Spacing, Post Height |
| `organic_blob` | "a large craggy rust asteroid" | Radius, Detail Level, Roughness, Feature Size, Tint R/G/B |

The operator catalogue (`catalogue.py`) currently covers 16 SOPs: `grid`, `box`, `sphere`, `tube`,
`line`, `xform`, `mountain::2.0`, `subdivide`, `polyextrude::2.0`, `color`, `scatter::2.0`,
`attribwrangle`, `copyxform`, `copytopoints::2.0`, `merge`, `null`.

## Evaluation

`evaluate.py` measures properties that can be checked without a human:

| Metric | Meaning |
|---|---|
| Builds | Script runs to completion in mock Houdini. |
| Native operators | Share of nodes that are standard Houdini operators (100% by design). |
| Commented nodes | Share of nodes carrying an explanation of their role. |
| Linked parameters | Parameters driven by artist controls vs. fixed literals. |
| Control liveness | Each control is perturbed by 10% of its range; it passes if any linked parameter changes. Controls read only inside VEX are reported separately because they need a real cook to verify. |

Current results on the four demo briefs: all build, 100% native operators, 100% of nodes commented,
every checkable control live, no dead controls. The test suite (27 tests) covers drafting,
every validator rule, wiring fidelity, control-to-parameter propagation, mock strictness, JSON
round-tripping and the CLI.

The **creative** side of the project's evaluation — editability in practice, creative control and
agency — needs studies with technical artists and is not addressed by these metrics.

## Repository layout

```
brief2net/
├── main.py                     # entry point (CLI + interactive)
├── brief2net/
│   ├── spec.py                 # NetworkSpec, NodeSpec, Connection, Control
│   ├── drafter.py              # rule-based baseline drafter
│   ├── llm_drafter.py          # optional LLM drafter (untested)
│   ├── recipes.py              # four network patterns
│   ├── catalogue.py            # allowed operators + parameter names
│   ├── validator.py            # the gate
│   ├── codegen.py              # spec → Houdini build script
│   ├── mock_hou.py             # strict stand-in for hou
│   ├── evaluate.py             # technical metrics
│   ├── preview.py              # network diagram
│   └── cli.py
├── houdini/
│   ├── brief2net_shelf_tool.py # in-Houdini entry point
│   └── harvest_catalogue.py    # verify names against a live Houdini
├── tests/test_brief2net.py
├── output/demo/                # generated example outputs
├── docs/
│   ├── brief2net_Beginners_Guide.docx
│   └── images/
├── start_here_windows.bat
├── start_here_mac_linux.sh
└── requirements.txt
```

New to Houdini or to the project? Start with the plain-English
[Beginner's Guide](docs/brief2net_Beginners_Guide.docx).

## Limitations

- **Not yet validated in Houdini.** All testing uses `mock_hou`. Operator and parameter names were
  written from documentation; `mountain::2.0`, `scatter::2.0`, `polyextrude::2.0` and
  `copytopoints::2.0` are marked medium-confidence and are the most likely to differ between
  versions. Run the harvester before relying on results.
- **No geometry is computed outside Houdini.** The mock proves a network would be *built* as
  specified, not that it *looks* right.
- **The default drafter is rule-based.** It handles four recipe families, numbers paired with nouns,
  and a fixed adjective list. It cannot invent new network structures.
- **The LLM drafter is untested.** It is included to show where generative methods plug in.
- **Houdini-specific output.** The spec and validator are tool-agnostic; only `codegen.py` targets
  Houdini.

## Roadmap

- [ ] Run `harvest_catalogue.py` and the four demo builds in Houdini Apprentice; publish results.
- [ ] Shared benchmark of briefs; compare rule baseline vs. LLM vs. vision-language drafters.
- [ ] Inverse procedural modelling: recover controls from a reference mesh or image.
- [ ] Bayesian optimisation over artist controls toward a target.
- [ ] Grow the operator catalogue and recipe library; allow the drafter to compose sub-networks.
- [ ] Cook-time checks in Houdini (polycount, bounds, errors per node).
- [ ] Study with technical artists on editability, creative control and agency.
- [ ] Explore a second node-based target to test portability of the spec.

## Research context

This prototype accompanies an application to a practice-based PhD on **AI-augmented procedural
node-graph authoring for technical artists**, using Houdini as the initial environment. The
project's three objectives are reflected directly in the code:

| Objective | In this repository |
|---|---|
| 1. Investigate AI-augmented procedural authoring | Typed spec as the AI↔Houdini contract; pluggable drafters; validator-driven repair |
| 2. Develop a working network-building tool | Native-only build scripts with promoted artist controls, undo, comments, shelf tool |
| 3. Evaluate technical and creative use | Automated technical metrics and tests; creative evaluation planned |

Potential applications include virtual production, real-time pipelines, games, animation and VFX,
where procedural networks are routinely built and adapted for new tasks.

## Licence

MIT — see [LICENSE](LICENSE).

**Author:** Olanrewaju Adams Agunloye ([LinkedIn](https://www.linkedin.com/in/digitallanre))
