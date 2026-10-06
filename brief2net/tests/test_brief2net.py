"""Run:  python -m unittest discover -s tests -v   (from the brief2net folder)"""
import copy
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brief2net.cli import DEMO_BRIEFS, build, main          # noqa: E402
from brief2net.codegen import SpecInvalid, generate         # noqa: E402
from brief2net.drafter import NoMatchingRecipe, RuleDrafter  # noqa: E402
from brief2net.evaluate import evaluate                     # noqa: E402
from brief2net.mock_hou import OperationFailed, dry_run     # noqa: E402
from brief2net.recipes import RECIPES                       # noqa: E402
from brief2net.spec import Connection, Control, NetworkSpec  # noqa: E402
from brief2net.validator import validate                    # noqa: E402

D = RuleDrafter()


class DrafterTests(unittest.TestCase):
    def test_picks_expected_recipe(self):
        expect = ["scatter_on_terrain", "stacked_tower", "fence", "organic_blob"]
        for brief, key in zip(DEMO_BRIEFS, expect):
            self.assertEqual(D.draft(brief).spec.recipe, key, brief)

    def test_reads_numbers(self):
        s = D.draft("a skyscraper with 45 floors").spec
        self.assertEqual(s.control("floor_count").default, 45)
        s = D.draft("scatter 1200 pebbles on the ground").spec
        self.assertEqual(s.control("instance_count").default, 1200)

    def test_explicit_number_beats_adjective(self):
        s = D.draft("a tall tower with 8 floors").spec
        self.assertEqual(s.control("floor_count").default, 8)

    def test_every_guess_is_recorded(self):
        d = D.draft("a sparse scatter of rocks")
        self.assertTrue(any("sparse" in a for a in d.assumptions))
        self.assertTrue(any("defaults" in a for a in d.assumptions))

    def test_refuses_to_guess(self):
        with self.assertRaises(NoMatchingRecipe):
            D.draft("a melancholy jazz soundtrack")

    def test_forced_recipe(self):
        self.assertEqual(D.draft("anything at all", recipe="fence").spec.recipe, "fence")


class ValidatorTests(unittest.TestCase):
    def good(self):
        return D.draft(DEMO_BRIEFS[0]).spec

    def test_all_recipes_pass(self):
        for key, r in RECIPES.items():
            rep = validate(r.build(r.defaults, ""))
            self.assertTrue(rep.ok, f"{key}: {rep}")

    def test_unknown_operator(self):
        s = self.good()
        s.nodes[0].type = "magic_rock_maker"
        self.assertFalse(validate(s).ok)

    def test_unknown_parm(self):
        s = self.good()
        s.nodes[0].parms["wibble"] = 3
        self.assertIn("no parameter 'wibble'", str(validate(s)))

    def test_cycle(self):
        s = self.good()
        s.connections.append(Connection("OUT", "terrain_grid"))
        self.assertIn("loop", str(validate(s)))

    def test_too_many_inputs(self):
        s = self.good()
        s.connections.append(Connection("piece_base", "OUT", 3))
        self.assertFalse(validate(s).ok)

    def test_dead_control(self):
        s = self.good()
        s.controls.append(Control("unused", "Unused", "float", 1, 0, 2))
        self.assertIn("not used by any node", str(validate(s)))

    def test_dangling_reference(self):
        s = self.good()
        s.node("terrain_noise").exprs["height"] = 'ch("../ghost")'
        self.assertIn("ghost", str(validate(s)))

    def test_default_out_of_range(self):
        s = self.good()
        s.controls[0].default = 1e9
        self.assertFalse(validate(s).ok)

    def test_reserved_control_name(self):
        s = self.good()
        s.controls[0].name = "tx"
        self.assertIn("clashes", str(validate(s)))

    def test_codegen_refuses_invalid(self):
        s = self.good()
        s.nodes[0].type = "nope"
        with self.assertRaises(SpecInvalid):
            generate(s)


class BuildTests(unittest.TestCase):
    def test_every_recipe_builds_in_mock(self):
        for key, r in RECIPES.items():
            spec = r.build(r.defaults, "")
            geo = dry_run(generate(spec))
            self.assertEqual(len(geo.children()), len(spec.nodes), key)
            self.assertTrue(geo.node(spec.output).display, key)

    def test_wiring_matches_spec(self):
        spec = D.draft(DEMO_BRIEFS[0]).spec
        geo = dry_run(generate(spec))
        for c in spec.connections:
            self.assertIs(geo.node(c.dst)._inputs[c.dst_input], geo.node(c.src))

    def test_controls_drive_parms(self):
        spec = D.draft("a tower with 10 floors").spec
        geo = dry_run(generate(spec))
        self.assertEqual(geo.node("stack_floors").parm("ncy").eval(), 10)
        geo.parm("floor_count").set(25)    # the artist edits a control...
        self.assertEqual(geo.node("stack_floors").parm("ncy").eval(), 25)
        self.assertAlmostEqual(geo.node("core").parm("sizey").eval(), 25 * 3.5)

    def test_mock_is_strict_about_parms(self):
        spec = D.draft("a fence").spec
        script = generate(spec).replace("parm('ncy')", "parm('ncopies')")
        with self.assertRaises(AttributeError):     # real hou would also fail here
            dry_run(script)

    def test_mock_is_strict_about_types(self):
        script = generate(D.draft("a fence").spec).replace("'copyxform'", "'copyxfrom'")
        with self.assertRaises(OperationFailed):
            dry_run(script)

    def test_script_is_standalone(self):
        script = generate(D.draft("an asteroid").spec)
        self.assertNotIn("brief2net.", script.split("import hou", 1)[1])

    def test_spec_json_roundtrip(self):
        spec = D.draft(DEMO_BRIEFS[1]).spec
        again = NetworkSpec.from_json(spec.to_json())
        self.assertEqual(generate(copy.deepcopy(again)).split("\n", 3)[3],
                         generate(spec).split("\n", 3)[3])


class EvaluationTests(unittest.TestCase):
    def test_all_controls_live_or_vex(self):
        for brief in DEMO_BRIEFS:
            ev = evaluate(D.draft(brief).spec)
            self.assertTrue(ev.builds)
            self.assertEqual(ev.dead_controls, [], brief)
            self.assertEqual(ev.native_ratio, 1.0)

    def test_detects_dead_control(self):
        spec = D.draft("a fence").spec
        spec.node("repeat_posts").exprs["ncy"] = "12"   # break the link
        spec.controls[0].drives = []
        spec.node("rail").exprs["sizex"] = "10"
        spec.node("rail").exprs["tx"] = "5"
        self.assertFalse(validate(spec).ok)            # validator catches it first


class CliTests(unittest.TestCase):
    def test_build_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            res = build(DEMO_BRIEFS[2], d, quiet=True)
            self.assertTrue(res["ok"])
            for suffix in (".spec.json", "_build.py", "_preview.png", "_report.md"):
                self.assertTrue(os.path.exists(os.path.join(d, "fence" + suffix)), suffix)

    def test_check_command(self):
        with tempfile.TemporaryDirectory() as d:
            res = build(DEMO_BRIEFS[3], d, quiet=True)
            self.assertEqual(main(["check", res["script"]]), 0)


if __name__ == "__main__":
    unittest.main()
