# Betting Strategy Overview

Concise reference for how weekly model picks are transformed into teaser / parlay combinations to balance edge capture, variance, and bankroll growth.

---
## 1. Philosophy
- Prioritize positive expected value (EV) derived from calibrated model win probabilities.
- Leverage teaser key-number movement to increase per-leg true win probability.
- Diversify outcome variance by mixing ticket sizes (2–4 legs primary) and limiting correlation.
- Apply strict bankroll risk caps and dynamic pruning (drop negative EV tickets before staking).

---
## 2. Inputs (Per Pick)
| Field | Description |
|-------|-------------|
| Game_Pick | Side chosen (team) |
| Base Line | Spread relative to picked team (resolve_line_for_pick) |
| Teaser Line | Base Line + teaser_adjust (e.g. +6) in favor of pick side |
| Pick_Prob | Model estimated win probability (after adjustments) |
| Moneyline Odds | Closing book price for pick side |
| Overall_Adv | Aggregate model edge metric (ranking) |

---
## 3. Ranking & Filtering
1. Rank picks by |Overall_Adv| descending (tie-break by Pick_Prob).  
2. Drop any pick with missing probability or material injury/news uncertainty.  
3. Optional: minimum threshold (e.g. Overall_Adv ≥ 2.0 or Pick_Prob ≥ 0.57 teased).

---
## 4. Teaser Construction
- Standard teaser: add +6 points (favorites move down, dogs move up).  
- Accept leg only if teaser crosses ≥1 key number (−3, −4, −6, −7) or pushes dog past +8.5/+10.  
- If no key movement, consider using straight line or exclude leg from teaser buckets.

---
## 5. Combination Generation
For pick set P (n picks): generate all combinations of sizes r ∈ [2, k] (k ≤ 4 typical, ≤ 8 supported in code).  
For each combo C with legs i=1..r:
```
Combined_Prob = Π p_i
Book_Dec_Odds = Π o_i
Fair_Dec_Odds = 1 / Combined_Prob
Book_Implied_Prob = 1 / Book_Dec_Odds
Edge = Combined_Prob - Book_Implied_Prob
EV(stake S) = Combined_Prob * (Book_Dec_Odds - 1) * S - (1 - Combined_Prob) * S
```
Reject combos with Edge ≤ 0 or EV ≤ 0 before staking.

---
## 6. Allocation Framework (Example)
| Bucket | Legs | Target Share of Weekly Risk | Rationale |
|--------|------|-----------------------------|-----------|
| A | 2-leg teasers | 50% | Higher hit rate, base growth |
| B | 3-leg teasers | 35% | Moderate variance, better payout |
| C | 4-leg parlay  | 15% | Controlled upside slice |

Guideline: Weekly Risk = 6–10% of current bankroll (e.g. Bankroll 1000 → Risk 8% = 80). Distribute by bucket share; within bucket use flat stakes (or mild edge weighting capped at 1.5× median).

---
## 7. Weekly Execution Checklist
1. Pull model picks + lines + probabilities.  
2. Rank & filter (injuries / thresholds).  
3. Compute teaser lines & validate key-number movement.  
4. Generate combos (sizes 2–4).  
5. Compute Combined_Prob, odds, Edge, EV.  
6. Drop negative EV or correlated duplicates (avoid >1 leg from same game).  
7. Allocate stakes per bucket until Risk Cap reached.  
8. Log tickets (CSV / DB) with: Legs, Lines (base & teaser), p_i, Combined_Prob, Odds, Stake, EV.  
9. After games: grade, update bankroll, variance metrics, recalibrate.

---
## 8. Example Week (Illustrative Numbers)
Assume 4 qualified picks (A,B,C,D) after filtering with (teaser-adjusted) win probs:

| Pick | Base Line | Teaser Line | Pick_Prob (p) | Dec Odds (o) |
|------|-----------|-------------|---------------|--------------|
| A | -7.5 | -1.5 | 0.64 | 1.87 |
| B | -2.5 | +3.5 | 0.62 | 1.83 |
| C | +1.5 | +7.5 | 0.60 | 1.95 |
| D | -3.0 | +3.0 | 0.58 | 1.90 |

Tickets (stake per plan: 2-leg $10, 3-leg $14, 4-leg $12):

| # | Legs | Combined_Prob | Book_Dec_Odds | Edge | EV ($) | Action |
|---|------|---------------|---------------|------|--------|--------|
| 1 | A+B | 0.64*0.62=0.397 | 1.87*1.83=3.42 | 0.397 - 0.292=0.105 | 0.397*(2.42*10) - 0.603*10 = $2.02 | Keep |
| 2 | A+C | 0.384 | 3.65 | 0.384 - 0.274=0.110 | $2.34 | Keep |
| 3 | B+C | 0.372 | 3.57 | 0.372 - 0.280=0.092 | $1.67 | Keep |
| 4 | A+D | 0.371 | 3.55 | 0.371 - 0.282=0.089 | $1.55 | Keep |
| 5 | A+B+C | 0.238 | 3.42*1.95=6.66 | 0.238 - 0.150=0.088 | EV≈ 0.238*(5.66*14)-0.762*14 = $1.02 | Borderline |
| 6 | A+B+D | 0.230 | 6.49 | 0.230 - 0.154=0.076 | $0.67 | Optional |
| 7 | A+B+C+D | 0.138 | 6.66*1.90=12.65 | 0.138 - 0.079=0.059 | EV≈ 0.138*(11.65*12)-0.862*12 = $0.27 | Small stake |

(If any EV ≤ 0, drop and reallocate its stake proportionally.)

---
## 9. Risk Controls
- Max exposure per single pick: ≤ 55% of total weekly risk weight (count appearances × stake).  
- Cap number of high-variance (≥4-leg) tickets to 1–2 unless bankroll growth > target.  
- Correlation filter: Do not include multiple sides from same game or legs with obviously linked outcomes (e.g., heavy weather cluster) in one ticket.  
- Stop reduction trigger: If realized drawdown > 2× expected weekly loss, cut remaining open higher-leg tickets (if cash-out or hedge possible).  
- Calibration audit monthly: Compare empirical win rates vs modeled Pick_Prob buckets.

---
## 10. Glossary
| Term | Meaning |
|------|---------|
| Combined_Prob | Product of leg win probabilities |
| Book_Dec_Odds | Product of decimal odds offered (parlay) |
| Fair_Dec_Odds | Reciprocal of Combined_Prob (no vig) |
| Edge | Combined_Prob − (1 / Book_Dec_Odds) |
| EV | Expected value of ticket given stake |
| Key Numbers | High-frequency margin values (3, 4, 6, 7, etc.) |

---
## Quick Copy Template
```
1. Rank & filter picks
2. Validate teaser key-number movement
3. Generate combos (2–4 legs)
4. Compute prob, odds, EV
5. Drop negative EV / correlated
6. Allocate stakes (risk %)
7. Log tickets
8. Post-week grading & calibration
```

---
**Note:** Adjust teaser points, bucket shares, and min edge thresholds as market conditions or model calibration evolve.

