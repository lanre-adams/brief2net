# ============================================================================
# brief2net 0.1.0 — generated Houdini build script
# Generated: 2026-10-06 11:22   Recipe: fence
# Brief:
#   A low wooden fence with 20 posts along a path.
# Assumptions made by the drafter (check these!):
#   - Read '20 posts' as post_count = 20.
#   - 'low' -> post_height x0.6 (now 0.72).
#   - Left at recipe defaults (brief did not say): post_spacing.
#   - Recipe chosen: 'Fence / railing' (keyword score 6; confidence high).
#
# HOW TO RUN: Houdini > Windows > Python Shell, then:
#   exec(open(r'/path/to/this_file.py').read())
# Everything it builds is a normal, editable Houdini node. Ctrl+Z undoes it.
# ============================================================================
import hou


def build(parent_path='/obj', name='fence'):
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
        folder.addParmTemplate(hou.IntParmTemplate('post_count', 'Posts', 1, default_value=(20,), min=2, max=500, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('post_spacing', 'Post Spacing', 1, default_value=(2.0,), min=0.3, max=10.0, help=''))
        folder.addParmTemplate(hou.FloatParmTemplate('post_height', 'Post Height', 1, default_value=(0.72,), min=0.3, max=5.0, help=''))
        ptg.append(folder)
        geo.setParmTemplateGroup(ptg)

        # ---- 2. Nodes (all native operators) ----
        n = {}
        n['post'] = geo.createNode('box', 'post')
        n['post'].setComment('One fence post, sitting on the ground')
        n['post'].parm('sizex').set(0.15)
        n['post'].parm('sizez').set(0.15)
        n['post'].parm('sizey').setExpression('ch("../post_height")', hou.exprLanguage.Hscript)
        n['post'].parm('ty').setExpression('ch("../post_height")*0.5', hou.exprLanguage.Hscript)
        n['repeat_posts'] = geo.createNode('copyxform', 'repeat_posts')
        n['repeat_posts'].setComment('Repeats the post along X')
        n['repeat_posts'].parm('ncy').setExpression('ch("../post_count")', hou.exprLanguage.Hscript)
        n['repeat_posts'].parm('tx').setExpression('ch("../post_spacing")', hou.exprLanguage.Hscript)
        n['rail'] = geo.createNode('box', 'rail')
        n['rail'].setComment('Top rail; length follows count x spacing')
        n['rail'].parm('sizey').set(0.08)
        n['rail'].parm('sizez').set(0.06)
        n['rail'].parm('sizex').setExpression('(ch("../post_count")*ch("../post_spacing"))-ch("../post_spacing")', hou.exprLanguage.Hscript)
        n['rail'].parm('tx').setExpression('((ch("../post_count")*ch("../post_spacing"))-ch("../post_spacing"))*0.5', hou.exprLanguage.Hscript)
        n['rail'].parm('ty').setExpression('ch("../post_height")*0.8', hou.exprLanguage.Hscript)
        n['lower_rail'] = geo.createNode('copyxform', 'lower_rail')
        n['lower_rail'].setComment('Duplicates the rail lower down')
        n['lower_rail'].parm('ncy').set(2)
        n['lower_rail'].parm('ty').setExpression('-ch("../post_height")*0.45', hou.exprLanguage.Hscript)
        n['combine'] = geo.createNode('merge', 'combine')
        n['combine'].setComment('Posts + rails together')
        n['OUT'] = geo.createNode('null', 'OUT')
        n['OUT'].setComment('Final output — display flag lives here')

        # ---- 3. Wiring ----
        n['repeat_posts'].setInput(0, n['post'], 0)
        n['lower_rail'].setInput(0, n['rail'], 0)
        n['combine'].setInput(0, n['repeat_posts'], 0)
        n['combine'].setInput(1, n['lower_rail'], 0)
        n['OUT'].setInput(0, n['combine'], 0)

        # ---- 4. Flags, layout and a note for the next person ----
        n['OUT'].setDisplayFlag(True)
        n['OUT'].setRenderFlag(True)
        geo.layoutChildren()
        sticky = geo.createStickyNote()
        sticky.setText('Built by brief2net from the brief:\nA low wooden fence with 20 posts along a path.\n\nEdit anything. Main knobs: container > Artist Controls tab.')
    return geo


result = build()
print('brief2net: built', result.path())
