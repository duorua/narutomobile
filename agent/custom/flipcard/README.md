# `flipcard/` — 4×4 Flip-Card Mini-Game Recognizer

This package implements the anniversary 4×4 flip-card puzzle solver. It was
extracted from a single 637-line god class (`FlipCard`) in Wave 3 of the
refactor so that the game logic can be **unit-tested without MAA** and the
MAA glue stays small and obvious.

## Module Layout

| File | Role | MAA-coupled? |
|------|------|-------------:|
| `grid.py`        | `CardGrid`, `OrangeInfo`, cell-type constants, geometric constants (`MAIN_DIAG`, `SUB_DIAG`), victory / unflipped / orange-info queries. | **No** |
| `strategy.py`    | `FlipStrategy` — greedy scoring for the initial and growth phases, including all tie-break rules and AI decision logging. | **No** (only `utils.logger`) |
| `recognition.py` | `FlipCardRecognition` — the MAA pipeline hook; calls `get_card_type` for each ROI, builds a `CardGrid`, delegates to `FlipStrategy`, and returns a `Rect` + `detail` payload. | **Yes** |
| `__init__.py`    | Re-exports `FlipCardRecognition` so the `@AgentServer.custom_recognition("FlipCard")` decorator fires on package import. | — |

## Why the split?

1. **Testability.** `grid.py` and `strategy.py` import zero MAA symbols, so
   `tests/integration/test_flipcard_flow.py` and any future unit tests can
   exercise the decision logic headlessly.
2. **Single responsibility.** The former god class mixed screen scraping,
   state tracking, and scoring into one 637-line blob. Each new file has one
   reason to change.
3. **Backwards compatibility.** The MAA pipeline still references the
   `"FlipCard"` task name — it continues to resolve because `__init__.py`
   imports `FlipCardRecognition`, which triggers the
   `@AgentServer.custom_recognition("FlipCard")` registration at import time.

## Adding a Test

Integration tests live in `tests/integration/`. A `FakeContext` in
`test_flipcard_flow.py` answers `run_recognition("card_0"|"card_1"|"card_wait", ...)`
against a caller-supplied 4×4 truth grid, so a test only needs to:

```python
from custom.flipcard.recognition import FlipCardRecognition

truth = [[1, 1, 1, 0], [0]*4, [0]*4, [0]*4]          # three purples in row 0
result = FlipCardRecognition().analyze(FakeContext(truth), argv())
assert result.detail["flip_pos"] == (1, 4)           # completes the row
```

No MAA runtime, no device, no screenshots on disk.

## Constants

All ROI / coordinate literals live in `agent/custom/constants.py`
(`CARD_4X4_ROI`, `FLIP_TIP_CLICK_ROI`). Do **not** hard-code pixels here.
