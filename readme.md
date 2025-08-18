<p align="center">
  <a href="https://github.com/ald1897/Panda-Picks/actions/workflows/ci.yml"><img src="https://github.com/ald1897/Panda-Picks/actions/workflows/ci.yml/badge.svg" alt="Build" /></a>
  <a href="https://codecov.io/gh/ald1897/Panda-Picks"><img src="https://img.shields.io/codecov/c/github/ald1897/Panda-Picks?logo=codecov&label=coverage" alt="Coverage" /></a>
  <a href="https://github.com/ald1897/Panda-Picks"><img src="https://img.shields.io/github/last-commit/ald1897/Panda-Picks" alt="Last Commit" /></a>
  <a href="https://github.com/ald1897/Panda-Picks/issues"><img src="https://img.shields.io/github/issues/ald1897/Panda-Picks" alt="Open Issues" /></a>
  <a href="https://github.com/ald1897/Panda-Picks/blob/main/LICENSE"><img src="https://img.shields.io/github/license/ald1897/Panda-Picks" alt="License" /></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Project Status" />
  <a href="https://raw.githubusercontent.com/ald1897/Panda-Picks/main/scripts/badges/roi.json"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ald1897/Panda-Picks/main/scripts/badges/roi.json" alt="ROI Season" /></a>
</p>

# Panda Picks

Panda Picks is a modular Python (3.11+) system that ingests NFL team grades & spreads, derives matchup advantages, generates probabilistic picks, tunes decision thresholds, trains a calibrated logistic model, and backtests (including probability calibration & teaser simulation). A NiceGUI UI provides interactive exploration.

---
## 1. Key Features
- Centralized configuration (`config/Settings`) with env overrides.
- Repository + service layers (easier testing & dependency injection).
- Advantage & engineered mismatch features feeding a logistic model.
- Threshold tuning producing ROI‑aware significance cutoffs.
- Backtest pipeline with probability calibration & teaser combinatorics.
- Unit + integration tests (probability math, metrics, probability metrics generation).

---
## 2. Updated Project Structure (Relevant Directories)
```
Panda-Picks/
  readme.md
  requirements.txt
  database/nfl_data.db            # SQLite database
  data/                           # Raw & derived CSV assets
    grades/ team_grades.csv ...
    picks/                        # (optionally ignored artifacts)
  docs/ TechSpec.md               # Detailed technical spec
  panda_picks/
    main.py                       # (Legacy) sequential startup script
    config/                       # Settings + legacy path constants
    data/                         # Ingestion scripts + repositories
    analysis/
      picks.py                    # Core batch pick generation (legacy style)
      backtest.py                 # Backtesting + calibration
      model_training.py           # Logistic regression training
      threshold_tuning.py         # Grid search for thresholds
      services/                   # New service layer (pick_service, metrics_service)
      models/                     # Domain dataclasses
      utils/probability.py        # Shared probability + simulation helpers
    db/database.py                # Table DDL + basic persistence
    ui/main.py                    # NiceGUI UI
    tests/                        # Unit & integration tests
```

---
## 3. Runtime Flow (Typical Batch)
1. Fetch grades (`panda_picks.data.get_pff_grades`).
2. Load grades into DB (`store_grades_data`).
3. Populate spreads (`analysis.spreads` script or external importer).
4. (Optional) Train model (`analysis.model_training`).
5. (Optional) Tune thresholds (`analysis.threshold_tuning`).
6. Generate picks (`analysis.picks` OR `PickService`).
7. Backtest & probability calibration (`analysis.backtest`).
8. Launch UI (`ui.main`) to inspect picks, backtest metrics, and team views.

---
## 4. Configuration
Centralized in `panda_picks/config/settings.py` & re-exported in `panda_picks/config/__init__.py`.

Environment variable overrides (examples):
| Variable | Purpose | Default |
|----------|---------|---------|
| `PANDA_ENV` | Environment mode | `development` |
| `PP_OVERALL_THRESH` | Overall advantage threshold | `2.0` |
| `PP_OFFENSE_THRESH` | Offense advantage threshold | `2.0` |
| `PP_DEFENSE_THRESH` | Defense advantage threshold | `2.0` |
| `PP_K_PROB_SCALE` | Logistic scale for fallback probability | `0.10` |
| `PP_EDGE_MIN` | Minimum edge to retain pick | `0.035` |
| `PP_MARGIN_K` | Margin mean scale factor | `0.75` |
| `PP_MARGIN_SD` | Margin standard deviation | `13.5` |
| `PP_SIM_SEED` | Global simulation seed | `123` |

You can set (PowerShell example):
```powershell
$env:PP_OVERALL_THRESH = "3.0"
```

---
## 5. Repositories & Services
- Repositories (`panda_picks.data.repositories.*`) encapsulate raw SQL → DataFrame.
- `PickService` orchestrates week-level pick generation using repositories and probability utilities (an incremental migration away from monolithic `picks.py`).
- `metrics_service.compute_model_accuracy` is a pure function for accuracy stats (supersedes deprecated `model_accuracy.py`).

---
## 6. Model Training & Threshold Tuning
| Module | Purpose | Output Tables |
|--------|---------|---------------|
| `analysis.model_training` | Trains logistic regression with time-based CV | `model_logit_coeffs`, `model_logit_scaler`, `model_logit_cv_metrics` |
| `analysis.threshold_tuning` | ROI + accuracy grid search for significance thresholds | `threshold_tuning_results` |

`picks.py` auto-loads the best tuning row to update in-memory thresholds (mutates `Settings.ADVANTAGE_THRESHOLDS`).

---
## 7. Backtesting & Calibration
`analysis.backtest`:
- Merges `picks` & `spreads` per week.
- Computes implied moneyline & spread probabilities; edges & calibration bins.
- Simulates missing scores if enabled.
- Generates teaser combination returns (2/3/4-team) & cumulative bankroll metrics.
- Produces tables: `probability_game_metrics`, `probability_calibration`, `probability_week_metrics`, `picks_results`, `teaser_results`, `backtest_results`.

---
## 8. Probability & Advantages
Advantages = Grade differentials (home minus opponent) + engineered mismatches:
- Pressure_Mismatch = Pass_Block_Adv − Pass_Rush_Adv
- Explosive_Pass_Mismatch = Receiving_Adv − Coverage_Adv
- Script_Control_Mismatch = Run_Block_Adv − Run_Defense_Adv

Probability path:
1. If logistic artifacts exist ⇒ standardized linear model + sigmoid.
2. Else fallback: `1 / (1 + exp(-K_PROB_SCALE * Overall_Adv))`.

Edge = Model Win Prob − Market Implied (moneyline). Picks filtered by `EDGE_MIN`.

---
## 9. Quick Start
```bash
# 1. Environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Initialize DB
python -c "from panda_picks.db.database import create_tables; create_tables()"

# 3. Grades ingestion
python -m panda_picks.data.get_pff_grades
python -c "from panda_picks.db.database import store_grades_data; store_grades_data()"

# 4. Spreads (sample generation / placeholder)
python -m panda_picks.analysis.spreads

# 5. (Optional) Train model
python -m panda_picks.analysis.model_training

# 6. (Optional) Tune thresholds
python -m panda_picks.analysis.threshold_tuning

# 7. Generate picks
python -m panda_picks.analysis.picks

# 8. Backtest
python -m panda_picks.analysis.backtest

# 9. Launch UI
python -m panda_picks.ui.main
```

Alternate (service usage inside Python):
```python
from panda_picks.analysis.services.pick_service import PickService
svc = PickService()
week_picks_df = svc.generate_picks_for_week(1)
print(week_picks_df[['WEEK','Home_Team','Away_Team','Game_Pick','Home_Win_Prob']])
```

---
## 10. Testing
Run all unit tests:
```bash
python -m unittest discover -v panda_picks/tests/unit
```
Integration test (probability metrics):
```bash
python -m unittest -v panda_picks.tests.integration.test_backtest_probability
```

---
## 11. Data Tables Overview (Selected)
| Table | Purpose |
|-------|---------|
| `grades` | Team grades snapshot |
| `spreads` | Matchup odds & lines |
| `picks` | Generated model picks & advantages |
| `threshold_tuning_results` | Threshold grid search results |
| `model_logit_coeffs` / `model_logit_scaler` | Logistic model artifacts |
| `picks_results` | Pick correctness & spread coverage |
| `teaser_results` | Teaser profitability by week |
| `probability_game_metrics` | Per-game probability vs implied edges |
| `probability_calibration` | Calibration curve bins |
| `probability_week_metrics` | Weekly Brier / LogLoss |
| `backtest_results` | Summary profit & bankroll progression |

---
## 12. UI Summary
`ui/main.py` (NiceGUI) shows:
- Summary stats (win rates, recent picks, upcoming games)
- Backtest triggers & charts
- Team detail insights (recent results, schedule, ATS record)

(Planned refactor: shift direct DB queries behind service functions.)

---
## 13. Deprecated / Transitional Components
| Component | Status | Notes |
|----------|--------|-------|
| `analysis/model_accuracy.py` | Deprecated stub | Use `metrics_service.compute_model_accuracy` |
| PDF-based grade scraping | Deprecated | Replaced by API ingestion (`get_pff_grades`) |
| Direct UI DB access | Transitional | To be abstracted behind services |

---
## 14. Roadmap (Abbreviated)
| Area | Next Step |
|------|-----------|
| Schema management | Introduce migrations (Alembic) |
| Pick pipeline | Full service/domain adoption |
| Calibration QA | Regression tests & dashboards |
| UI API layer | FastAPI or similar wrapper |
| Portfolio modeling | Bankroll & bet sizing strategies |

---
## 15. Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty picks | Missing spreads/grades | Re-run ingestion steps |
| Logistic model ignored | No model artifact tables | Run model_training module |
| Thresholds unchanged | No tuning results | Run threshold_tuning module |
| Backtest KeyError on odds | Older code path or missing columns | Regenerate picks; ensure spreads have odds |
| Calibration tables empty | No Home_Win_Prob in picks | Train model or ensure fallback prob executed |

Enable debug logs (PowerShell):
```powershell
$env:PANDA_ENV = "development"
python -m panda_picks.analysis.picks
```

---
## 16. License & Contributions
License: MIT (see [LICENSE](LICENSE)).
Contributions welcome: open issues for feature ideas; submit PRs with tests.

---
## 17. Further Reading
- `docs/TechSpec.md` – architecture & deep dive.
- `docs/roadmap.md` – prioritized enhancements.
- `docs/userinterface.md` – UI layout notes.

---
Happy building – extend responsibly, measure calibration, and iterate.
