### Phase 0 (Prep – 1 short PR)
- Add week column + z_score + raw metric columns to advanced_stats (or create advanced_stats_extended).
- Actually call advanced stats collector in main.start().
- Backfill existing daily CSV into DB for Week 1 (or current week) to validate.
### Phase 1 (Data + Feature Layer)
- Create module analysis/advanced_features.py: build_team_week_features(conn, season, week) -> team-level features (off_composite, def_composite, momentum, trend). build_matchup_features(conn, season, week) -> rows (week, home, away, Off_Comp_Diff, Def_Comp_Diff, Net_Composite, pressure_mismatch, turnover_index).
- Persist matchup features in new table matchup_features(season, week, home, away, ...).
### Phase 2 (Incorporate Into Picks)
- In picks.makePicks join matchup_features.
- Store Off_Comp_Diff, Def_Comp_Diff, Net_Composite in picks table (add nullable columns).
- Replace or augment Overall_Adv with blended: blended_adv = α * Overall_Adv + (1-α) * Net_Composite_norm (temp α=0.6).
### Phase 3 (Calibration & Simple Model)
- Historical regression (prior seasons if available; else early-season holdout) to map Net_Composite to margin (linear).
- Derive Expected_Margin and Cover_Prob (logistic on margin - spread).
- Add columns: Expected_Margin, Cover_Prob, Model_Edge, Confidence_Score to picks.
- Threshold logic: only flag pick if Model_Edge ≥ min_edge (config).
### Phase 4 (Schedule Adjustment + Momentum)
- Add opponent strength normalization (subtract average opponent composite).
- Add rolling 3-week form + slope; integrate into model (refit).
### Phase 5 (Backtest Enhancements)
- Extend backtest() to run baseline vs advanced vs blended; compute ROI, Brier, Calibration bins.
- Output comparison report (CSV + console).
### Phase 6 (Risk & Sizing)
- Implement fractional Kelly (cap).
- Add stake column to picks_results.
### Phase 7 (Refinement)
- Feature importance logging, drift checks, alert if missing new week advanced stats before picks.
### Minimal initial execution order this week

- Schema migration + ingestion call.
- Feature builder (team + matchup).
- Join into picks with new diffs.
- Simple linear margin estimate (hard-coded coefficients from quick fit or provisional).
- Backtest comparison toggle.

Deliverable sequencing (each PR small) PR1: Migration + ingestion call + tests for new table. PR2: Feature builder + table + unit test on one synthetic matchup. PR3: Picks integration + new columns. PR4: Backtest enhancements + report. PR5: Simple model calibration utility.


### Key shortcuts / assumptions early
Use current season only; momentum uses prior weeks; if week <3 fallback to season average.
If missing metric, impute league mean and flag (impute_flag column).

### Stop criteria after Phase 1–3
Picks table shows new feature columns populated.
Backtest shows delta performance metrics recorded.
Start with PR1. Let me know if you want me to implement Phase 0–1 now.