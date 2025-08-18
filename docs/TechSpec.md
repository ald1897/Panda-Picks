# Panda-Picks Technical Specification

_Last updated: 2025-08-18_

## 1. Purpose & Scope
Panda-Picks is a modular NFL prediction and betting analysis system. It ingests grades & odds data, derives matchup advantages, generates picks with probabilities, tunes thresholds, trains a calibrated logistic model, backtests results (including probability calibration), and serves a UI for exploration.

This document describes each Python package and script, the runtime flow (data → predictions → backtest → UI), and the evolving architecture (legacy vs refactored layers).

---
## 2. High-Level Architecture

```
            +------------------+          +------------------+
            |  External Data   |          |   User Actions   |
            | (PFF API / CSVs) |          |   (UI / CLI)     |
            +---------+--------+          +---------+--------+
                      |                             |
                      v                             v
              +---------------+            +------------------+
              |  Data Layer   |<---------->|       UI Layer   |
              | (Ingestion &  |            |  (nicegui pages) |
              |   Repos)      |            +------------------+
                      |
                      v
              +---------------+  thresholds  +--------------------+
              |  Domain &     |<------------>| Threshold Tuning   |
              |  Services     |              +--------------------+
                      |
                      v  model coeffs
              +---------------+ <------------+  Model Training    |
              |  Prediction   |              +--------------------+
              |  Generation   |
                      |
                      v
              +---------------+  simulated   +--------------------+
              |   Backtest    |<------------>|  Simulation Logic  |
              +---------------+               (in analysis code)
                      |
                      v
              +---------------+
              | Metrics / DB  |
              +---------------+
```

### Layer Summary
| Layer | Responsibility | Key Modules |
|-------|----------------|-------------|
| Configuration | Centralized runtime constants | `config/settings.py`, `config/__init__.py` |
| Data Acquisition | Fetch & preprocess external raw data | `data/get_pff_grades.py`, `data/advanced_stats.py`, (PDF flow deprecated) |
| Database Schema/Access | Table creation & low-level ops | `db/database.py` |
| Repositories | Abstract SQL → DataFrames | `data/repositories/*.py` |
| Domain Models | Typed entities for logic | `analysis/models/` |
| Services | Business orchestration | `analysis/services/pick_service.py`, `metrics_service.py` |
| Core Analysis | Prediction logic, tuning, training, backtest | `analysis/picks.py`, `threshold_tuning.py`, `model_training.py`, `backtest.py`, `bets.py`, `spreads.py` |
| Utilities | Shared math/util logic | `analysis/utils/probability.py` |
| UI | User interaction & display | `ui/main.py`, `ui/router.py` |
| Testing | Unit & integration validation | `tests/unit/*`, `tests/integration/*` |

---
## 3. Execution Flow (End-to-End)
A typical full run triggered by `python -m panda_picks.main` (or equivalent startup script) proceeds:

1. (Optional legacy step) Drop & recreate tables (see `main.py` logic – currently still doing a reset).
2. Fetch PFF grades via `data/get_pff_grades.py`:
   - API call → normalized DataFrame → CSV persisted to `data/grades/team_grades.csv`.
3. Store grades into DB via `db/database.store_grades_data` (loads CSV → `grades` table).
4. (Advanced stats placeholder) `data/advanced_stats.py` updates/augments stats (currently minimal / stub).
5. Generate spreads snapshots via `analysis/spreads.py` (populates `spreads` table) – obtains or simulates lines.
6. Generate picks via `analysis/picks.py.makePicks()`:
   - Merges spreads + grades.
   - Computes advantages & engineered mismatch features.
   - Loads tuned thresholds (if available) & logistic coefficients (if trained).
   - Calculates probabilities and edges.
   - Applies edge / significance filters; writes rows to `picks`.
7. Backtest via `analysis/backtest.py.backtest()`:
   - Joins `picks` + `spreads` per week.
   - Optionally simulates missing scores.
   - Computes implied probabilities, calibration metrics, edges, teaser outcomes.
   - Stores results in `picks_results`, `teaser_results`, probability metric tables.
8. UI (`ui/main.py`) surfaces aggregated metrics (requires tables populated).
9. Optional tasks:
   - Threshold tuning (`analysis/threshold_tuning.tune_thresholds`) updates `threshold_tuning_results` (affects future pick generation).
   - Model training (`analysis/model_training.train`) produces logistic coefficients & scaler stats (`model_logit_*` tables).

---
## 4. Configuration Layer (`config/`)
- `settings.py`: Central constants (advantage thresholds, probability scaling, simulation parameters, paths). Offers runtime override via env vars and dynamic updates from tuning.
- `__init__.py`: Exposes legacy file path constants (CSV/PDF resources) while aligning with new Settings model.

**Key Settings**
- `ADVANTAGE_THRESHOLDS`: Dict for `Overall_Adv`, `Offense_Adv`, `Defense_Adv`.
- `K_PROB_SCALE`: Logistic scaling factor for fallback probability.
- Simulation knobs: `SIM_K_MARGIN`, `SIM_BASE_TOTAL`, `SIM_TOTAL_JITTER`.
- File paths: `TEAM_GRADES_CSV`, `PFF_TEAM_GRADES_PDF` etc.

---
## 5. Data Acquisition (`panda_picks/data/`)
- `get_pff_grades.py`: Fetches raw PFF JSON, transforms to normalized grade columns (OVR, OFF, DEF, PASS, etc.). Saves CSV.
- `advanced_stats.py`: Placeholder for extended metrics (currently minimal or stub hooks).
- `repositories/`:
  - `spread_repository.py`: Query spreads by week.
  - `grade_repository.py`: Load & normalize grades (TEAM→Home_Team).
  - `pick_repository.py`: Persist & retrieve picks rows idempotently.

**Legacy/Deprecated**: `pdf_scraper.py` replaced by API ingestion (removed here) – old PDF approach no longer primary.

---
## 6. Database Layer (`db/database.py`)
Implements:
- `get_connection()`: SQLite connection using configured path.
- `create_tables()`: Idempotent schema creation.
- `drop_tables()`: Reset utility.
- `store_grades_data()`: CSV → `grades`.

Tables include `grades`, `spreads`, `picks`, `picks_results`, `teaser_results`, `backtest_results`, model artifacts tables, tuning tables, and probability calibration tables.

**Note**: Refactor path introduces potential future `connection.py` (repository pattern). Current code still uses this monolithic file.

---
## 7. Domain Models (`analysis/models/`)
- `team.py`: `Team` dataclass with grade attributes (overall/offense/defense + granular metrics).
- `prediction_model.py`: Dataclasses: `Matchup`, `Advantage`, `Prediction` (structure for typed service return objects). Adoption incremental; core pick logic still DataFrame-based.

---
## 8. Utility Layer (`analysis/utils/probability.py`)
- `calculate_win_probability(advantage)`: Logistic transform using `Settings.K_PROB_SCALE`.
- `simulate_score(advantage)`: Stochastic score generation (used in tuning/backtest contexts for missing data). Seeded RNG for reproducibility.

---
## 9. Service Layer (`analysis/services/`)
### `pick_service.py`
Encapsulates week-level pick generation using repositories & probability util. Steps:
1. Load spreads for week.
2. Join with grades (home & away perspective).
3. Compute basis advantages (delegates to shared lambdas from `picks.py`).
4. Classify significance vs thresholds (runtime updatable).
5. Compute logistic fallback probabilities.
6. Filter out neutral picks.
7. Persist to DB via repository.

### `metrics_service.py`
- `compute_model_accuracy(picks_df, results_df)`: Pure function that produces overall & weekly accuracy (replaces deprecated `model_accuracy.py` logic). Used in tests; can integrate into UI for KPI dashboards.

---
## 10. Core Analysis Modules (`analysis/`)
### `picks.py`
Primary batch predictor (legacy + enhanced features). Functions:
- Advantage calculations & engineered features: `Pressure_Mismatch`, `Explosive_Pass_Mismatch`, `Script_Control_Mismatch`.
- Significance classification: uses tuned OR default thresholds.
- Probability computation: loads logistic model artifacts (`model_logit_coeffs`, `model_logit_scaler`); falls back to sigmoid over `Overall_Adv` otherwise.
- Edge calculation: market implied probabilities vs model; filters by `EDGE_MIN`.
- Cover probability: Normal approximation using `MARGIN_K`, `MARGIN_SD`.
- Persistence: Adds any missing columns to `picks` table; per-week overwrite (delete then insert).

**Bridging**: Maintains column naming expected by backtest & UI (e.g., `Game_Pick`, `Overall_Adv_sig`).

### `threshold_tuning.py`
Grid search for thresholds (`Overall_Adv`, `Offense_Adv`, `Defense_Adv`):
1. Builds dataset (grades + spreads + computed advantages).
2. Simulates scores if missing.
3. Applies each threshold combination; records accuracy & ROI (moneyline profit proxy).
4. Writes `threshold_tuning_results` sorted by ROI → Accuracy → Picks.
5. `picks.py` loads top row to refresh runtime thresholds.

### `model_training.py`
Logistic regression cross-time validation:
1. Build dataset with engineered mismatches.
2. Time-split CV across weeks (progressive training windows).
3. Evaluate Brier, LogLoss, AUC.
4. Train final model on all completed games; persist coefficients + scaler stats.
5. `picks.py` loads coefficients at runtime for calibrated probabilities.

### `backtest.py`
- Iterates over weeks merging `picks` + `spreads`.
- Consolidates duplicate line & odds columns (post-merge `_x`, `_y`).
- Simulates scores (optional) to fill gaps.
- Computes implied probabilities (moneyline & spread) + derived edges.
- Produces calibration artifacts:
  - `probability_game_metrics`: per-game predicted vs implied.
  - `probability_calibration`: binned predicted vs actual frequencies.
  - `probability_week_metrics`: Brier / LogLoss weekly summary.
- Evaluates teaser combinations (2,3,4 team) & profitability.
- Writes `picks_results`, `teaser_results`, `backtest_results`.
- Cleans deprecated columns before persistence (avoid schema bloat).

### `spreads.py`
Generates / ingests line data (structure-dependent). Provides a `main` callable used by startup to populate `spreads` table.

### `bets.py`
Contains spread adjustment utilities (`adjust_spread`) and betting combinatorics referenced by backtest (teaser logic). Some of its functions became embedded in `backtest.py`; potential future consolidation.

### `model_accuracy.py` (Deprecated Stub)
Previously computed pick correctness; superseded by `metrics_service.py`. Kept temporarily for backward compatibility – scheduled for removal.

---
## 11. UI Layer (`ui/`)
### `main.py`
- NiceGUI entrypoint constructing dashboard components:
  - Summary stats (total picks, win rates, upcoming games).
  - Backtest triggers and results sections.
  - Team detail views (grades, recent results, schedule, ATS record).
  - Picks generation and display (calls generation indirectly via DB state).
- Router integration via `router.py` & `router_frame.js` for multi-page navigation.

**Data Access Pattern**: UI directly queries DB (legacy approach). Future plan: delegate to service layer endpoints or internal adapters for looser coupling & testability.

---
## 12. Testing (`tests/`)
- Unit:
  - `test_probability.py`: Validates logistic probability transformation.
  - `test_metrics_service.py`: Accuracy metric computation.
- Integration:
  - `test_backtest_probability.py`: Ensures probability metrics tables populate after backtest (uses isolated temp DB file).

**Future Enhancements**:
- Add repository contract tests (in-memory DB).
- Golden output comparison for pick generation.
- Calibration regression tests to detect model drift.

---
## 13. Data & Schema Overview
| Table | Purpose | Populated By |
|-------|---------|--------------|
| `grades` | Team grade metrics (per snapshot) | CSV import (`store_grades_data`) |
| `spreads` | Weekly matchup odds/lines | `spreads.py` / ingestion scripts |
| `picks` | Model picks & advantages | `picks.py` / `pick_service.py` |
| `threshold_tuning_results` | Threshold grid search results | `threshold_tuning.py` |
| `model_logit_coeffs` | Logistic regression coefficients | `model_training.py` |
| `model_logit_scaler` | Feature scaling stats | `model_training.py` |
| `picks_results` | Result evaluation per game | `backtest.py` |
| `teaser_results` | Teaser combo profitability | `backtest.py` |
| `backtest_results` | Aggregated/summary profit | `backtest.py` |
| `probability_game_metrics` | Per-game prob metrics & edges | `backtest.py` |
| `probability_calibration` | Binned calibration view | `backtest.py` |
| `probability_week_metrics` | Weekly Brier/LogLoss summaries | `backtest.py` |

---
## 14. Probability & Advantage Computation
- Base advantages derived by subtracting opponent-adjusted grades (vector of lambda transforms in `picks.py`).
- Engineered mismatch features provide additional signals for logistic model (pressure, explosive pass, script control proxies).
- Probability path:
  1. If `model_logit_coeffs` & scaler present → standardized logistic inference.
  2. Else fallback: `sigmoid(K_PROB_SCALE * Overall_Adv)`.
- Edges:
  - Moneyline implied prob = American odds conversion, normalized.
  - Spread implied home win probability via Normal margin approximation.
  - Pick edge = model win prob − market implied prob (moneyline). Filter by `EDGE_MIN`.

---
## 15. Threshold Tuning Strategy
- Balanced objective: ROI per pick primary, then accuracy, then pick volume.
- One-sided significance rule: Only pick if at least one advantage crosses threshold without any opposing significant advantage.
- Persisted best thresholds automatically loaded on subsequent pick generation.

---
## 16. Backtesting & Calibration
- Simulated scores fill missing historical outcomes to preserve continuity; flagged via `Simulated_Score`.
- Calibration tables allow inspection of prob calibration (predicted vs empirical win frequencies).
- Weekly metrics enable tracking predictive reliability drift.

---
## 17. Logging Strategy
- Extensive INFO logs for data pipeline stages (grades, spreads, picks, backtest).
- Threshold/model loading logs clarify runtime path (calibrated vs fallback).
- Backtest column schema mutation logs suppressed for duplicates (now debug-level suppressed).

**Improvement Targets**:
- Structured logging (JSON) for ingestion metrics.
- Log correlation IDs per run/session.

---
## 18. Known Technical Debt & Roadmap (Highlights)
| Area | Issue | Planned Action |
|------|-------|----------------|
| UI Data Access | Direct DB queries from UI | Introduce service facade / API boundary |
| Mixed Paradigms | DF-centric logic vs dataclasses | Gradual migration of picks/backtest to typed domain objects |
| Config Mutation | Global dict mutation for thresholds | Introduce immutable snapshot pattern per run |
| Schema Evolution | Repeated ALTERs in runtime | Offline migration scripts / Alembic integration |
| Test Coverage | Limited integration scenarios | Expand to multi-week golden tests & edge cases |
| Performance | Recomputing advantages weekly | Cache intermediate advantage frames (week-based) |

---
## 19. Deployment & Environment Assumptions
- Single-file SQLite DB (not concurrent write-heavy). Scaling path: replace with Postgres + migrations.
- Assumes synchronous CLI or UI-triggered batch runs; no task queue yet.
- Randomness controlled via seeds for reproducibility in simulation & logistic fallback scenarios.

---
## 20. Extension Points
| Extension | Hook Point | Notes |
|-----------|-----------|-------|
| Alternate Models | Add new table of coefficients; update loader to prefer latest by timestamp | Keep fallback orderly |
| Additional Features | Extend advantage lambda list | Retrain logistic model afterward |
| API Exposure | Wrap service layer with FastAPI/Flask | Reuse `PickService` & metrics service |
| Live Odds Ingestion | New repository + scheduler | APScheduler already in requirements |
| Portfolio Optimization | Add Kelly / bankroll mgmt module | Use existing edge + prob metrics |

---
## 21. Removal / Deprecation List
| Component | Status | Replacement |
|-----------|--------|------------|
| `model_accuracy.py` | Deprecated stub | `metrics_service.py` |
| PDF scraping flow | Deprecated | API ingestion (`get_pff_grades.py`) |
| Direct UI DB queries | To be deprecated | Service abstraction |

---
## 22. Glossary
| Term | Meaning |
|------|---------|
| Advantage | Difference in a grade (home − opponent) or engineered mismatch |
| Edge | Model probability vs market implied probability delta |
| Calibration | Alignment of predicted probabilities with actual outcomes |
| Teaser | Multi-team adjusted-spread bet simulated in backtest |
| Thresholds | Advantage magnitude cutoffs for pick significance |

---
## 23. Quick Developer Onboarding
```bash
# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -c "from panda_picks.db.database import create_tables; create_tables()"
python -m panda_picks.data.get_pff_grades  # fetch grades
python -c "from panda_picks.db.database import store_grades_data; store_grades_data()"
python -m panda_picks.analysis.spreads     # generate spreads
python -m panda_picks.analysis.picks       # generate picks
python -m panda_picks.analysis.backtest    # run backtest
python -m panda_picks.analysis.model_training  # (optional) calibrate model
python -m panda_picks.analysis.threshold_tuning # (optional) tune thresholds
python -m panda_picks.ui.main              # launch UI
```

---
## 24. Change Log (TechSpec)
| Date | Summary |
|------|---------|
| 2025-08-18 | Initial comprehensive spec drafted post refactor (config centralization, services, probability calibration tables). |

---
## 25. Open Questions
- Should thresholds be stored versioned with model artifacts for reproducibility?
- Introduce feature importance pipeline post-training for explainability?
- Migrate from implicit table mutation to schema migrations (Alembic)?

---
**End of Document**

