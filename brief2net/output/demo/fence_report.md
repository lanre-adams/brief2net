# fence — brief2net report

**Brief:** A low wooden fence with 20 posts along a path.

## Assumptions
- Read '20 posts' as post_count = 20.
- 'low' -> post_height x0.6 (now 0.72).
- Left at recipe defaults (brief did not say): post_spacing.
- Recipe chosen: 'Fence / railing' (keyword score 6; confidence high).

## Technical evaluation
| Check | Result |
|---|---|
| Builds in mock Houdini | yes |
| Nodes / wires | 6 / 5 |
| Native operators | 100% |
| Nodes with an explanatory comment | 100% |
| Artist controls exposed | 3 |
| Parameters linked to controls | 8 of 13 set |
| Controls proven live (perturbation test) | 3/3 |
| Controls read inside VEX (needs real cook to verify) | none |

## Artist controls
| Control | Default | Range | Drives |
|---|---|---|---|
| Posts | 20 | 2–500 | repeat_posts.ncy, rail.sizex, rail.tx |
| Post Spacing | 2 | 0.3–10 | repeat_posts.tx, rail.sizex, rail.tx |
| Post Height | 0.72 | 0.3–5 | post.sizey, post.ty, rail.ty, lower_rail.ty |
