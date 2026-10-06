# stacked_tower — brief2net report

**Brief:** A tall twisting tower, 30 floors, twisting 3 degrees per floor.

## Assumptions
- Read '30 floors' as floor_count = 30.
- Read '3 degrees' as twist = 3.
- Left at recipe defaults (brief did not say): floor_height, floor_width, floor_depth.
- Recipe chosen: 'Stacked / twisting tower' (keyword score 11; confidence high).

## Technical evaluation
| Check | Result |
|---|---|
| Builds in mock Houdini | yes |
| Nodes / wires | 5 / 4 |
| Native operators | 100% |
| Nodes with an explanatory comment | 100% |
| Artist controls exposed | 5 |
| Parameters linked to controls | 9 of 10 set |
| Controls proven live (perturbation test) | 5/5 |
| Controls read inside VEX (needs real cook to verify) | none |

## Artist controls
| Control | Default | Range | Drives |
|---|---|---|---|
| Floors | 30 | 1–200 | stack_floors.ncy, core.sizey, core.ty |
| Floor Height | 3.5 | 1–10 | stack_floors.ty, core.sizey, core.ty |
| Floor Width | 20 | 2–100 | floor_slab.sizex, core.sizex |
| Floor Depth | 20 | 2–100 | floor_slab.sizez, core.sizez |
| Twist per Floor (deg) | 3 | -45–45 | stack_floors.ry |
