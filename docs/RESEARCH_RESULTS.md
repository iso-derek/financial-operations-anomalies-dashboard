# Synthetic audit experiment — 2026-10-05

25,000 generated transactions, seed 42; fictional fixed USD conversion rates. Training 15,023, validation 4,935, test 4,938; 104 later cross-partition invoice repeats purged. Each method receives 494 test review slots. Validation selected the hybrid with ML weight .25.

| Method | Precision @ 494 | Recall @ 494 | Labelled anomaly USD equivalent |
|---|---:|---:|---:|
| Rules | 47.37% | 82.69% | 25,257,370 |
| Isolation Forest | 42.31% | 73.85% | 26,283,260 |
| Hybrid | 51.42% | 89.75% | 26,537,380 |

The hybrid improves yield in this particular planted dataset. The generator and rules share similar assumptions, so these results do not establish real-world fraud performance. Large nominal amounts and fictional rates also limit economic interpretation. Values above are rounded and are not savings.

Input CSV SHA-256: `7e86cb5453b775851ecfa0b28419250e8b99695ec5eba00bec4aad38dcfb8a1c`.

Reproduce with `python scripts/run_research.py`. The dashboard uses a smaller 5,000-record demonstration and therefore shows different measurements.
