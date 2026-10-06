# scatter_on_terrain — brief2net report

**Brief:** A dense field of jagged rocks scattered across hilly terrain, about 800 rocks, 150 metres wide.

## Assumptions
- Read '800 rocks' as instance_count = 800.
- Read '150 metres' as terrain_size = 150.
- 'hilly' -> terrain_height x2.0 (now 12).
- 'jagged' -> piece_roughness x2.0 (now 0.7).
- Left at recipe defaults (brief did not say): seed, min_scale, max_scale.
- Recipe chosen: 'Scatter objects on terrain' (keyword score 10; confidence high).

## Technical evaluation
| Check | Result |
|---|---|
| Builds in mock Houdini | yes |
| Nodes / wires | 9 / 9 |
| Native operators | 100% |
| Nodes with an explanatory comment | 100% |
| Artist controls exposed | 7 |
| Parameters linked to controls | 6 of 15 set |
| Controls proven live (perturbation test) | 5/5 |
| Controls read inside VEX (needs real cook to verify) | min_scale, max_scale |

## Artist controls
| Control | Default | Range | Drives |
|---|---|---|---|
| Terrain Size | 150 | 5–500 | terrain_grid.sizex, terrain_grid.sizey |
| Hill Height | 12 | 0–50 | terrain_noise.height |
| Object Count | 800 | 1–20000 | scatter_pts.npts |
| Random Seed | 1 | 0–1000 | scatter_pts.seed |
| Min Scale | 0.3 | 0.01–10 | read in VEX |
| Max Scale | 1.2 | 0.01–10 | read in VEX |
| Roughness | 0.7 | 0–2 | piece_rough.height |
