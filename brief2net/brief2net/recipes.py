"""Recipe library: hand-checked network patterns the drafter can instantiate.

A recipe is a *function* that takes a small set of artistic values and returns
a complete NetworkSpec. Every number an artist would plausibly want to change
is promoted as a Control and linked into the network with ch("../name"),
so the result stays editable after it is built.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from .spec import Connection, Control, NetworkSpec, NodeSpec


def ch(name: str) -> str:
    """HScript reference from a node inside the geo container to a control on it."""
    return f'ch("../{name}")'


class Recipe:
    def __init__(self, key: str, title: str, keywords: Dict[str, float],
                 defaults: Dict[str, float], number_hints: Dict[str, List[str]],
                 build: Callable[[Dict[str, float], str], NetworkSpec], summary: str):
        self.key, self.title, self.keywords = key, title, keywords
        self.defaults, self.number_hints = defaults, number_hints
        self.build, self.summary = build, summary


# ---------------------------------------------------------------------------
# 1. Scatter objects on a terrain
# ---------------------------------------------------------------------------
def _scatter_on_terrain(v: Dict[str, float], brief: str) -> NetworkSpec:
    s = NetworkSpec(name="scatter_on_terrain", recipe="scatter_on_terrain", brief=brief)
    s.nodes = [
        NodeSpec("terrain_grid", "grid", {"rows": 120, "cols": 120},
                 {"sizex": ch("terrain_size"), "sizey": ch("terrain_size")},
                 note="Ground plane; size follows the Terrain Size control"),
        NodeSpec("terrain_noise", "mountain::2.0", {"elementsize": 8.0},
                 {"height": ch("terrain_height")},
                 note="Rolling hills via fractal noise"),
        NodeSpec("scatter_pts", "scatter::2.0", {},
                 {"npts": ch("instance_count"), "seed": ch("seed")},
                 note="Where the objects will sit"),
        NodeSpec("scale_and_spin", "attribwrangle", {
            "class": 2,  # points
            "snippet": (
                "// Random size and rotation per point (edit freely)\n"
                "float r = rand(@ptnum + ch(\"../seed\"));\n"
                "@pscale = fit01(r, ch(\"../min_scale\"), ch(\"../max_scale\"));\n"
                "float a = rand(@ptnum * 7.13) * 2 * PI;\n"
                "p@orient = quaternion(a, {0,1,0});\n")},
            note="Readable VEX: per-point scale between Min/Max Scale, random yaw"),
        NodeSpec("piece_base", "sphere", {"type": 2, "freq": 3},
                 note="Low-poly sphere as the base for each scattered piece"),
        NodeSpec("piece_rough", "mountain::2.0", {"elementsize": 0.4},
                 {"height": ch("piece_roughness")},
                 note="Breaks up the sphere so pieces look like rocks"),
        NodeSpec("place_pieces", "copytopoints::2.0", {"pack": 1},
                 note="Copies one piece onto every scattered point (packed for speed)"),
        NodeSpec("combine", "merge", note="Terrain + pieces together"),
        NodeSpec("OUT", "null", note="Final output — display flag lives here"),
    ]
    s.connections = [
        Connection("terrain_grid", "terrain_noise"),
        Connection("terrain_noise", "scatter_pts"),
        Connection("scatter_pts", "scale_and_spin"),
        Connection("piece_base", "piece_rough"),
        Connection("piece_rough", "place_pieces", 0),
        Connection("scale_and_spin", "place_pieces", 1),
        Connection("terrain_noise", "combine", 0),
        Connection("place_pieces", "combine", 1),
        Connection("combine", "OUT"),
    ]
    s.controls = [
        Control("terrain_size", "Terrain Size", "float", v["terrain_size"], 5, 500,
                ["terrain_grid.sizex", "terrain_grid.sizey"], "Width of the ground in metres"),
        Control("terrain_height", "Hill Height", "float", v["terrain_height"], 0, 50,
                ["terrain_noise.height"], "How tall the hills are"),
        Control("instance_count", "Object Count", "int", v["instance_count"], 1, 20000,
                ["scatter_pts.npts"], "How many objects are scattered"),
        Control("seed", "Random Seed", "float", v["seed"], 0, 1000,
                ["scatter_pts.seed"], "Change for a different arrangement"),
        Control("min_scale", "Min Scale", "float", v["min_scale"], 0.01, 10, [],
                "Smallest object size (read inside the wrangle)"),
        Control("max_scale", "Max Scale", "float", v["max_scale"], 0.01, 10, [],
                "Largest object size (read inside the wrangle)"),
        Control("piece_roughness", "Roughness", "float", v["piece_roughness"], 0, 2,
                ["piece_rough.height"], "How lumpy each object is"),
    ]
    return s


# ---------------------------------------------------------------------------
# 2. Stacked / twisting tower
# ---------------------------------------------------------------------------
def _stacked_tower(v: Dict[str, float], brief: str) -> NetworkSpec:
    s = NetworkSpec(name="stacked_tower", recipe="stacked_tower", brief=brief)
    s.nodes = [
        NodeSpec("floor_slab", "box", {"sizey": 0.3},
                 {"sizex": ch("floor_width"), "sizez": ch("floor_depth")},
                 note="One floor plate"),
        NodeSpec("stack_floors", "copyxform", {},
                 {"ncy": ch("floor_count"), "ty": ch("floor_height"), "ry": ch("twist")},
                 note="Repeats the floor upward; Twist rotates each floor"),
        NodeSpec("core", "box", {},
                 {"sizex": f'{ch("floor_width")}*0.35', "sizez": f'{ch("floor_depth")}*0.35',
                  "sizey": f'{ch("floor_count")}*{ch("floor_height")}',
                  "ty": f'{ch("floor_count")}*{ch("floor_height")}*0.5'},
                 note="Central core whose height follows floors x floor height"),
        NodeSpec("combine", "merge", note="Floors + core together"),
        NodeSpec("OUT", "null", note="Final output — display flag lives here"),
    ]
    s.connections = [
        Connection("floor_slab", "stack_floors"),
        Connection("stack_floors", "combine", 0),
        Connection("core", "combine", 1),
        Connection("combine", "OUT"),
    ]
    s.controls = [
        Control("floor_count", "Floors", "int", v["floor_count"], 1, 200,
                ["stack_floors.ncy", "core.sizey", "core.ty"]),
        Control("floor_height", "Floor Height", "float", v["floor_height"], 1, 10,
                ["stack_floors.ty", "core.sizey", "core.ty"]),
        Control("floor_width", "Floor Width", "float", v["floor_width"], 2, 100,
                ["floor_slab.sizex", "core.sizex"]),
        Control("floor_depth", "Floor Depth", "float", v["floor_depth"], 2, 100,
                ["floor_slab.sizez", "core.sizez"]),
        Control("twist", "Twist per Floor (deg)", "float", v["twist"], -45, 45,
                ["stack_floors.ry"]),
    ]
    return s


# ---------------------------------------------------------------------------
# 3. Fence / railing
# ---------------------------------------------------------------------------
def _fence(v: Dict[str, float], brief: str) -> NetworkSpec:
    s = NetworkSpec(name="fence", recipe="fence", brief=brief)
    length = f'{ch("post_count")}*{ch("post_spacing")}'
    s.nodes = [
        NodeSpec("post", "box", {"sizex": 0.15, "sizez": 0.15},
                 {"sizey": ch("post_height"), "ty": f'{ch("post_height")}*0.5'},
                 note="One fence post, sitting on the ground"),
        NodeSpec("repeat_posts", "copyxform", {},
                 {"ncy": ch("post_count"), "tx": ch("post_spacing")},
                 note="Repeats the post along X"),
        NodeSpec("rail", "box", {"sizey": 0.08, "sizez": 0.06},
                 {"sizex": f"({length})-{ch('post_spacing')}",
                  "tx": f"(({length})-{ch('post_spacing')})*0.5",
                  "ty": f'{ch("post_height")}*0.8'},
                 note="Top rail; length follows count x spacing"),
        NodeSpec("lower_rail", "copyxform", {"ncy": 2},
                 {"ty": f'-{ch("post_height")}*0.45'},
                 note="Duplicates the rail lower down"),
        NodeSpec("combine", "merge", note="Posts + rails together"),
        NodeSpec("OUT", "null", note="Final output — display flag lives here"),
    ]
    s.connections = [
        Connection("post", "repeat_posts"),
        Connection("rail", "lower_rail"),
        Connection("repeat_posts", "combine", 0),
        Connection("lower_rail", "combine", 1),
        Connection("combine", "OUT"),
    ]
    s.controls = [
        Control("post_count", "Posts", "int", v["post_count"], 2, 500,
                ["repeat_posts.ncy", "rail.sizex", "rail.tx"]),
        Control("post_spacing", "Post Spacing", "float", v["post_spacing"], 0.3, 10,
                ["repeat_posts.tx", "rail.sizex", "rail.tx"]),
        Control("post_height", "Post Height", "float", v["post_height"], 0.3, 5,
                ["post.sizey", "post.ty", "rail.ty", "lower_rail.ty"]),
    ]
    return s


# ---------------------------------------------------------------------------
# 4. Organic blob / asteroid
# ---------------------------------------------------------------------------
def _organic_blob(v: Dict[str, float], brief: str) -> NetworkSpec:
    s = NetworkSpec(name="organic_blob", recipe="organic_blob", brief=brief)
    s.nodes = [
        NodeSpec("base", "sphere", {"type": 2, "freq": 6},
                 {"radx": ch("radius"), "rady": ch("radius"), "radz": ch("radius")},
                 note="Starting sphere; size follows Radius"),
        NodeSpec("smooth", "subdivide", {}, {"iterations": ch("detail")},
                 note="Adds resolution so the noise has something to push"),
        NodeSpec("surface_noise", "mountain::2.0", {},
                 {"height": ch("roughness"), "elementsize": ch("feature_size")},
                 note="Lumps and craters via fractal noise"),
        NodeSpec("tint", "color", {"class": 1},
                 {"colorr": ch("tint_r"), "colorg": ch("tint_g"), "colorb": ch("tint_b")},
                 note="Base colour for look-dev"),
        NodeSpec("OUT", "null", note="Final output — display flag lives here"),
    ]
    s.connections = [Connection("base", "smooth"), Connection("smooth", "surface_noise"),
                     Connection("surface_noise", "tint"), Connection("tint", "OUT")]
    s.controls = [
        Control("radius", "Radius", "float", v["radius"], 0.1, 100,
                ["base.radx", "base.rady", "base.radz"]),
        Control("detail", "Detail Level", "int", v["detail"], 0, 4, ["smooth.iterations"],
                "Each step roughly quadruples polygons — keep low"),
        Control("roughness", "Roughness", "float", v["roughness"], 0, 5, ["surface_noise.height"]),
        Control("feature_size", "Feature Size", "float", v["feature_size"], 0.05, 20,
                ["surface_noise.elementsize"]),
        Control("tint_r", "Tint Red", "float", v["tint_r"], 0, 1, ["tint.colorr"]),
        Control("tint_g", "Tint Green", "float", v["tint_g"], 0, 1, ["tint.colorg"]),
        Control("tint_b", "Tint Blue", "float", v["tint_b"], 0, 1, ["tint.colorb"]),
    ]
    return s


RECIPES: Dict[str, Recipe] = {r.key: r for r in [
    Recipe("scatter_on_terrain", "Scatter objects on terrain",
           {"scatter": 3, "rock": 3, "rocks": 3, "boulder": 3, "pebble": 2, "terrain": 3,
            "ground": 2, "landscape": 2, "hill": 2, "hills": 2, "field": 1, "forest": 2,
            "tree": 1, "trees": 1, "debris": 2, "strewn": 2, "desert": 1},
           dict(terrain_size=100, terrain_height=6, instance_count=300, seed=1,
                min_scale=0.3, max_scale=1.2, piece_roughness=0.35),
           {"instance_count": ["rock", "rocks", "boulder", "boulders", "object", "objects",
                               "pebble", "pebbles", "tree", "trees", "piece", "pieces",
                               "instance", "instances", "points"],
            "terrain_size": ["metre", "meter", "m", "metres", "meters", "wide", "across"]},
           _scatter_on_terrain, "Noisy terrain with many randomly sized, rotated pieces on it"),
    Recipe("stacked_tower", "Stacked / twisting tower",
           {"tower": 3, "building": 3, "skyscraper": 3, "floor": 2, "floors": 2,
            "storey": 2, "storeys": 2, "stories": 2, "twist": 2, "twisting": 2, "high-rise": 3,
            "stack": 1, "stacked": 2},
           dict(floor_count=12, floor_height=3.5, floor_width=20, floor_depth=20, twist=0),
           {"floor_count": ["floor", "floors", "storey", "storeys", "stories", "levels", "level"],
            "twist": ["degree", "degrees", "deg"]},
           _stacked_tower, "Repeated floor plates around a core, optional twist per floor"),
    Recipe("fence", "Fence / railing",
           {"fence": 4, "railing": 3, "rail": 2, "post": 2, "posts": 2, "picket": 3,
            "barrier": 2, "balustrade": 3},
           dict(post_count=12, post_spacing=2.0, post_height=1.2),
           {"post_count": ["post", "posts", "picket", "pickets", "section", "sections"]},
           _fence, "Posts repeated along a line with two rails"),
    Recipe("organic_blob", "Organic blob / asteroid",
           {"asteroid": 4, "blob": 3, "organic": 2, "rock-like": 1, "planet": 2,
            "lumpy": 2, "meteor": 3, "moon": 2, "noisy": 1, "creature": 1, "egg": 1},
           dict(radius=2.0, detail=2, roughness=0.6, feature_size=0.8,
                tint_r=0.55, tint_g=0.5, tint_b=0.45),
           {"radius": ["radius", "metre", "meter", "m"]},
           _organic_blob, "A single lumpy, noise-displaced, tinted form"),
]}
