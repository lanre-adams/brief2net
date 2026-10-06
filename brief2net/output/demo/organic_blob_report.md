# organic_blob — brief2net report

**Brief:** A large craggy rust asteroid for a space shot.

## Assumptions
- 'craggy' -> roughness x2.5 (now 1.5).
- 'large' -> radius x2.5 (now 5).
- Colour word 'rust' -> tint (0.55, 0.3, 0.18).
- Left at recipe defaults (brief did not say): detail, feature_size.
- Recipe chosen: 'Organic blob / asteroid' (keyword score 4; confidence high).

## Technical evaluation
| Check | Result |
|---|---|
| Builds in mock Houdini | yes |
| Nodes / wires | 5 / 4 |
| Native operators | 100% |
| Nodes with an explanatory comment | 100% |
| Artist controls exposed | 7 |
| Parameters linked to controls | 9 of 12 set |
| Controls proven live (perturbation test) | 7/7 |
| Controls read inside VEX (needs real cook to verify) | none |

## Artist controls
| Control | Default | Range | Drives |
|---|---|---|---|
| Radius | 5 | 0.1–100 | base.radx, base.rady, base.radz |
| Detail Level | 2 | 0–4 | smooth.iterations |
| Roughness | 1.5 | 0–5 | surface_noise.height |
| Feature Size | 0.8 | 0.05–20 | surface_noise.elementsize |
| Tint Red | 0.55 | 0–1 | tint.colorr |
| Tint Green | 0.3 | 0–1 | tint.colorg |
| Tint Blue | 0.18 | 0–1 | tint.colorb |
