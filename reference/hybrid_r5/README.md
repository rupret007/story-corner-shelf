# Story Corner hybrid r5 fallback

This directory preserves the source configuration and generator for the verified `triadic_palatine_fitted_l_corner_r5` fallback. That revision used a black PETG Triadic Palatine finish over a plywood-and-steel shelf chassis. It is **not** the active 100%-printed shelf requested for r6.

The r5 fallback completed its deterministic 22-test regression suite, model-only 3MF archive validation, watertight/single-body mesh checks, 180 mm saved-orientation envelope checks, and repository consistency audit. It made no tested load-rating claim and contained no embedded G-code.

- `config.hybrid.json` is the frozen r5 configuration.
- `scripts/generate_hybrid_r5.py` is the frozen r5 generator source.
- The tracked source can regenerate its own isolated
  `reference/hybrid_r5/generated/` tree. That tree is ignored so hybrid output
  cannot be mistaken for the active r6 artifacts.

Do not mix r5 hybrid cut dimensions, fascia channels, or load-path instructions into the all-PETG r6 build.
