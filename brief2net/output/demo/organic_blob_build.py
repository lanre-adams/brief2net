# ============================================================================
# brief2net 0.1.0 — generated Houdini build script
# Generated: 2026-10-06 11:22   Recipe: organic_blob
# Brief:
#   A large craggy rust asteroid for a space shot.
# Assumptions made by the drafter (check these!):
#   - 'craggy' -> roughness x2.5 (now 1.5).
#   - 'large' -> radius x2.5 (now 5).
#   - Colour word 'rust' -> tint (0.55, 0.3, 0.18).
#   - Left at recipe defaults (brief did not say): detail, feature_size.
#   - Recipe chosen: 'Organic blob / asteroid' (keyword score 4; confidence
#     high).
#
# HOW TO RUN: Houdini > Windows > Python Shell, then:
#   exec(open(r'/path/to/this_file.py').read())
# Everything it builds is a normal, editable Houdini node. Ctrl+Z undoes it.
# ============================================================================
import hou


def build(parent_path='/obj', name='organic_blob'):
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
        folder.addParmTemplate(hou.FloatParmTemplate('radius', 'Radius', 1, default_value=(5.0,), min=0.1, max=100.0, help=''))
        folder.addParmTemplate(hou.IntParmTemplate('detail', 'Detail Level', 1, default_value=(2,), min=0, max=4, help='Each step roughly quadruples polygons — keep low'))
        folder.addParmTemplate(hou.FloatParmTemplate('roughness', 'Roughness', 1, default_value=(1.5,), min=0.0, max=5.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('feature_size', 'Feature Size', 1, default_value=(0.8,), min=0.05, max=20.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('tint_r', 'Tint Red', 1, default_value=(0.55,), min=0.0, max=1.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('tint_g', 'Tint Green', 1, default_value=(0.3,), min=0.0, max=1.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('tint_b', 'Tint Blue', 1, default_value=(0.18,), min=0.0, max=1.0, help=''))
        ptg.append(folder)
        geo.setParmTemplateGroup(ptg)

        # ---- 2. Nodes (all native operators) ----
        n = {}
        n['base'] = geo.createNode('sphere', 'base')
        n['base'].setComment('Starting sphere; size follows Radius')
        n['base'].parm('type').set(2)
        n['base'].parm('freq').set(6)
        n['base'].parm('radx').setExpression('ch("../radius")', hou.exprLanguage.Hscript)
        n['base'].parm('rady').setExpression('ch("../radius")', hou.exprLanguage.Hscript)
        n['base'].parm('radz').setExpression('ch("../radius")', hou.exprLanguage.Hscript)
        n['smooth'] = geo.createNode('subdivide', 'smooth')
        n['smooth'].setComment('Adds resolution so the noise has something to push')
        n['smooth'].parm('iterations').setExpression('ch("../detail")', hou.exprLanguage.Hscript)
        n['surface_noise'] = geo.createNode('mountain::2.0', 'surface_noise')
        n['surface_noise'].setComment('Lumps and craters via fractal noise')
        n['surface_noise'].parm('height').setExpression('ch("../roughness")', hou.exprLanguage.Hscript)
        n['surface_noise'].parm('elementsize').setExpression('ch("../feature_size")', hou.exprLanguage.Hscript)
        n['tint'] = geo.createNode('color', 'tint')
        n['tint'].setComment('Base colour for look-dev')
        n['tint'].parm('class').set(1)
        n['tint'].parm('colorr').setExpression('ch("../tint_r")', hou.exprLanguage.Hscript)
        n['tint'].parm('colorg').setExpression('ch("../tint_g")', hou.exprLanguage.Hscript)
        n['tint'].parm('colorb').setExpression('ch("../tint_b")', hou.exprLanguage.Hscript)
        n['OUT'] = geo.createNode('null', 'OUT')
        n['OUT'].setComment('Final output — display flag lives here')

        # ---- 3. Wiring ----
        n['smooth'].setInput(0, n['base'], 0)
        n['surface_noise'].setInput(0, n['smooth'], 0)
        n['tint'].setInput(0, n['surface_noise'], 0)
        n['OUT'].setInput(0, n['tint'], 0)

        # ---- 4. Flags, layout and a note for the next person ----
        n['OUT'].setDisplayFlag(True)
        n['OUT'].setRenderFlag(True)
        geo.layoutChildren()
        sticky = geo.createStickyNote()
        sticky.setText('Built by brief2net from the brief:\nA large craggy rust asteroid for a space shot.\n\nEdit anything. Main knobs: container > Artist Controls tab.')
    return geo


result = build()
print('brief2net: built', result.path())
