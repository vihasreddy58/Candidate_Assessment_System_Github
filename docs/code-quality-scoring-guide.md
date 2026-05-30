# Repository Quality Scoring Guide (Current)

This guide summarizes how repository code-quality scores are computed in `backend/services/code_quality_analyzer.py` and surfaced in the report via `backend/services/report_generator.py`.

For a full, implementation-level explanation (including worked examples, optional dependency behavior, and dynamic calibration), see `docs/scoring-deep-dive.md`.

## What the Report/Frontend Shows

The dashboard reads `report.codeQualityReport.categoryScores` (portfolio-level averages across analyzed repositories):

- `documentation`
- `codeOrganization`
- `commitQuality`
- `codeHealth` (only when Code Health is enabled and available)

Notes:
- LICENSE/tests/CI-CD signals are intentionally excluded from scoring in the current analyzer.
- Code Health is optional and may be unavailable depending on repo contents and installed libraries.

## Score bounds

All component scores are clamped to `0..100`.

## Category calculations (per repository)

### 1) Documentation (0–100)

Signals:
- README quality score × `0.65`
- `+18` if a docs folder exists at repo root (`docs/`, `doc/`, …)
- `+10` if an architecture/design doc exists at root (e.g., `architecture.md`)
- `+10` if an examples/demo folder exists at root
- `+7` if README includes a usage signal
- `+10` if `CONTRIBUTING.md` exists at root

### 2) Code Organization (0–100)

Formula:
- Base by structure label: `excellent=100`, `good=75`, `basic=50`, `minimal=25`
- Richness bonus: `min(15, directory_count * 1.5)`
- Final: `base * 0.85 + richness_bonus`

### 3) Commit Quality (0–100)

Formula:
- `0.45 * commit_frequency_score + 0.55 * commit_message_score`

Commit message quality includes an anti-repetition penalty when RapidFuzz is available.

### 4) Code Health (0–100, optional)

If enabled, this analyzes real source files (.py/.js/.ts/.java) using Radon/Esprima/Javalang when available.

## Per-repo totals and portfolio totals

- Per-repo total: weighted average of the categories present (weights are re-normalized if optional categories are missing).
- Portfolio overall score: weighted average of repo scores, weighted by stars and recency.
