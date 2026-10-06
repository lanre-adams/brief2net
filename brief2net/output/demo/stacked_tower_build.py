# ============================================================================
# brief2net 0.1.0 — generated Houdini build script
# Generated: 2026-10-06 11:22   Recipe: stacked_tower
# Brief:
#   A tall twisting tower, 30 floors, twisting 3 degrees per floor.
# Assumptions made by the drafter (check these!):
#   - Read '30 floors' as floor_count = 30.
#   - Read '3 degrees' as twist = 3.
#   - Left at recipe defaults (brief did not say): floor_height, floor_width,
#     floor_depth.
#   - Recipe chosen: 'Stacked / twisting tower' (keyword score 11; confidence
#     high).
#
# HOW TO RUN: Houdini > Windows > Python Shell, then:
#   exec(open(r'/path/to/this_file.py').read())
# Everything it builds is a normal, editable Houdini node. Ctrl+Z undoes it.
# ============================================================================
import hou


def build(parent_path='/obj', name='stacked_tower'):
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
        folder.addParmTemplate(hou.IntParmTemplate('floor_count', 'Floors', 1, default_value=(30,), min=1, max=200, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('floor_height', 'Floor Height', 1, default_value=(3.5,), min=1.0, max=10.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('floor_width', 'Floor Width', 1, default_value=(20.0,), min=2.0, max=100.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('floor_depth', 'Floor Depth', 1, default_value=(20.0,), min=2.0, max=100.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('twist', 'Twist per Floor (deg)', 1, default_value=(3.0,), min=-45.0, max=45.0, help=''))
        ptg.append(folder)
        geo.setParmTemplateGroup(ptg)

        # ---- 2. Nodes (all native operators) ----
        n = {}
        n['floor_slab'] = geo.createNode('box', 'floor_slab')
        n['floor_slab'].setComment('One floor plate')
        n['floor_slab'].parm('sizey').set(0.3)
        n['floor_slab'].parm('sizex').setExpression('ch("../floor_width")', hou.exprLanguage.Hscript)
        n['floor_slab'].parm('sizez').setExpression('ch("../floor_depth")', hou.exprLanguage.Hscript)
        n['stack_floors'] = geo.createNode('copyxform', 'stack_floors')
        n['stack_floors'].setComment('Repeats the floor upward; Twist rotates each floor')
        n['stack_floors'].parm('ncy').setExpression('ch("../floor_count")', hou.exprLanguage.Hscript)
        n['stack_floors'].parm('ty').setExpression('ch("../floor_height")', hou.exprLanguage.Hscript)
        n['stack_floors'].parm('ry').setExpression('ch("../twist")', hou.exprLanguage.Hscript)
        n['core'] = geo.createNode('box', 'core')
        n['core'].setComment('Central core whose height follows floors x floor height')
        n['core'].parm('sizex').setExpression('ch("../floor_width")*0.35', hou.exprLanguage.Hscript)
        n['core'].parm('sizez').setExpression('ch("../floor_depth")*0.35', hou.exprLanguage.Hscript)
        n['core'].parm('sizey').setExpression('ch("../floor_count")*ch("../floor_height")', hou.exprLanguage.Hscript)
        n['core'].parm('ty').setExpression('ch("../floor_count")*ch("../floor_height")*0.5', hou.exprLanguage.Hscript)
        n['combine'] = geo.createNode('merge', 'combine')
        n['combine'].setComment('Floors + core together')
        n['OUT'] = geo.createNode('null', 'OUT')
        n['OUT'].setComment('Final output — display flag lives here')

        # ---- 3. Wiring ----
        n['stack_floors'].setInput(0, n['floor_slab'], 0)
        n['combine'].setInput(0, n['stack_floors'], 0)
        n['combine'].setInput(1, n['core'], 0)
        n['OUT'].setInput(0, n['combine'], 0)

        # ---- 4. Flags, layout and a note for the next person ----
        n['OUT'].setDisplayFlag(True)
        n['OUT'].setRenderFlag(True)
        geo.layoutChildren()
        sticky = geo.createStickyNote()
        sticky.setText('Built by brief2net from the brief:\nA tall twisting tower, 30 floors, twisting 3 degrees per floor.\n\nEdit anything. Main knobs: container > Artist Controls tab.')
    return geo


result = build()
print('brief2net: built', result.path())
