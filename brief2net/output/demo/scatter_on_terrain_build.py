# ============================================================================
# brief2net 0.1.0 — generated Houdini build script
# Generated: 2026-10-06 11:22   Recipe: scatter_on_terrain
# Brief:
#   A dense field of jagged rocks scattered across hilly terrain, about 800
#   rocks, 150 metres wide.
# Assumptions made by the drafter (check these!):
#   - Read '800 rocks' as instance_count = 800.
#   - Read '150 metres' as terrain_size = 150.
#   - 'hilly' -> terrain_height x2.0 (now 12).
#   - 'jagged' -> piece_roughness x2.0 (now 0.7).
#   - Left at recipe defaults (brief did not say): seed, min_scale, max_scale.
#   - Recipe chosen: 'Scatter objects on terrain' (keyword score 10; confidence
#     high).
#
# HOW TO RUN: Houdini > Windows > Python Shell, then:
#   exec(open(r'/path/to/this_file.py').read())
# Everything it builds is a normal, editable Houdini node. Ctrl+Z undoes it.
# ============================================================================
import hou


def build(parent_path='/obj', name='scatter_on_terrain'):
    """Build the network and return the geometry container node."""
    parent = hou.node(parent_path)
    if parent is None:
        raise RuntimeError('Parent network %s not found' % parent_path)
    base, i = name, 1
    while parent.node(name) is not None:   # never overwrite existing work
        i += 1
        name = '%s_%d' % (base, i)

    with hou.undos.group('brief2net: build ' + name):
        geo = parent.createNode('geo', name)
        for child in geo.children():        # start from an empty container
            child.destroy()

        # ---- 1. Artist controls (top of the container's parameter pane) ----
        ptg = geo.parmTemplateGroup()
        folder = hou.FolderParmTemplate('artist_controls', 'Artist Controls')
        folder.addParmTemplate(hou.FloatParmTemplate('terrain_size', 'Terrain Size', 1, default_value=(150.0,), min=5.0, max=500.0, help='Width of the ground in metres'))
        folder.addParmTemplate(hou.FloatParmTemplate('terrain_height', 'Hill Height', 1, default_value=(12.0,), min=0.0, max=50.0, help='How tall the hills are'))
        folder.addParmTemplate(hou.IntParmTemplate('instance_count', 'Object Count', 1, default_value=(800,), min=1, max=20000, help='How many objects are scattered'))
        folder.addParmTemplate(hou.FloatParmTemplate('seed', 'Random Seed', 1, default_value=(1.0,), min=0.0, max=1000.0, help='Change for a different arrangement'))
        folder.addParmTemplate(hou.FloatParmTemplate('min_scale', 'Min Scale', 1, default_value=(0.3,), min=0.01, max=10.0, help='Smallest object size (read inside the wrangle)'))
        folder.addParmTemplate(hou.FloatParmTemplate('max_scale', 'Max Scale', 1, default_value=(1.2,), min=0.01, max=10.0, help='Largest object size (read inside the wrangle)'))
        folder.addParmTemplate(hou.FloatParmTemplate('piece_roughness', 'Roughness', 1, default_value=(0.7,), min=0.0, max=2.0, help='How lumpy each object is'))
        ptg.append(folder)
        geo.setParmTemplateGroup(ptg)

        # ---- 2. Nodes (all native operators) ----
        n = {}
        n['terrain_grid'] = geo.createNode('grid', 'terrain_grid')
        n['terrain_grid'].setComment('Ground plane; size follows the Terrain Size control')
        n['terrain_grid'].parm('rows').set(120)
        n['terrain_grid'].parm('cols').set(120)
        n['terrain_grid'].parm('sizex').setExpression('ch("../terrain_size")', hou.exprLanguage.Hscript)
        n['terrain_grid'].parm('sizey').setExpression('ch("../terrain_size")', hou.exprLanguage.Hscript)
        n['terrain_noise'] = geo.createNode('mountain::2.0', 'terrain_noise')
        n['terrain_noise'].setComment('Rolling hills via fractal noise')
        n['terrain_noise'].parm('elementsize').set(8.0)
        n['terrain_noise'].parm('height').setExpression('ch("../terrain_height")', hou.exprLanguage.Hscript)
        n['scatter_pts'] = geo.createNode('scatter::2.0', 'scatter_pts')
        n['scatter_pts'].setComment('Where the objects will sit')
        n['scatter_pts'].parm('npts').setExpression('ch("../instance_count")', hou.exprLanguage.Hscript)
        n['scatter_pts'].parm('seed').setExpression('ch("../seed")', hou.exprLanguage.Hscript)
        n['scale_and_spin'] = geo.createNode('attribwrangle', 'scale_and_spin')
        n['scale_and_spin'].setComment('Readable VEX: per-point scale between Min/Max Scale, random yaw')
        n['scale_and_spin'].parm('class').set(2)
        n['scale_and_spin'].parm('snippet').set('// Random size and rotation per point (edit freely)\nfloat r = rand(@ptnum + ch("../seed"));\n@pscale = fit01(r, ch("../min_scale"), ch("../max_scale"));\nfloat a = rand(@ptnum * 7.13) * 2 * PI;\np@orient = quaternion(a, {0,1,0});\n')
        n['piece_base'] = geo.createNode('sphere', 'piece_base')
        n['piece_base'].setComment('Low-poly sphere as the base for each scattered piece')
        n['piece_base'].parm('type').set(2)
        n['piece_base'].parm('freq').set(3)
        n['piece_rough'] = geo.createNode('mountain::2.0', 'piece_rough')
        n['piece_rough'].setComment('Breaks up the sphere so pieces look like rocks')
        n['piece_rough'].parm('elementsize').set(0.4)
        n['piece_rough'].parm('height').setExpression('ch("../piece_roughness")', hou.exprLanguage.Hscript)
        n['place_pieces'] = geo.createNode('copytopoints::2.0', 'place_pieces')
        n['place_pieces'].setComment('Copies one piece onto every scattered point (packed for speed)')
        n['place_pieces'].parm('pack').set(1)
        n['combine'] = geo.createNode('merge', 'combine')
        n['combine'].setComment('Terrain + pieces together')
        n['OUT'] = geo.createNode('null', 'OUT')
        n['OUT'].setComment('Final output — display flag lives here')

        # ---- 3. Wiring ----
        n['terrain_noise'].setInput(0, n['terrain_grid'], 0)
        n['scatter_pts'].setInput(0, n['terrain_noise'], 0)
        n['scale_and_spin'].setInput(0, n['scatter_pts'], 0)
        n['piece_rough'].setInput(0, n['piece_base'], 0)
        n['place_pieces'].setInput(0, n['piece_rough'], 0)
        n['place_pieces'].setInput(1, n['scale_and_spin'], 0)
        n['combine'].setInput(0, n['terrain_noise'], 0)
        n['combine'].setInput(1, n['place_pieces'], 0)
        n['OUT'].setInput(0, n['combine'], 0)

        # ---- 4. Flags, layout and a note for the next person ----
        n['OUT'].setDisplayFlag(True)
        n['OUT'].setRenderFlag(True)
        geo.layoutChildren()
        sticky = geo.createStickyNote()
        sticky.setText('Built by brief2net from the brief:\nA dense field of jagged rocks scattered across hilly terrain, about 800 rocks, 150 metres wide.\n\nEdit anything. Main knobs: container > Artist Controls tab.')
    return geo


result = build()
print('brief2net: built', result.path())
