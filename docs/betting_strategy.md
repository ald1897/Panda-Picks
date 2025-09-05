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
## 6. Weekly Execution Checklist
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
## 7. Allocation Framework (Example)
| Bucket | Legs | Target Share of Weekly Risk | Rationale |
|--------|------|-----------------------------|-----------|
| A | 2-leg teasers | 50% | Higher hit rate, base growth |
| B | 3-leg teasers | 35% | Moderate variance, better payout |
| C | 4-leg parlay  | 15% | Controlled upside slice |

Guideline: Weekly Risk = 6–10% of current bankroll (e.g. Bankroll 1000 → Risk 8% = 80). Distribute by bucket share; within bucket use flat stakes (or mild edge weighting capped at 1.5× median).

---
## 8. Example Week (Illustrative Numbers)
Assume 6 qualified picks (A–F) after filtering with (teaser-adjusted) win probs:

| Pick | Base Line | Teaser Line | Pick_Prob (p) | Market Dec Odds (o) |
|------|-----------|-------------|---------------|---------------------|
| A    | -7.5 | -1.5 | 0.64 | 1.90                |
| B    | -2.5 | +3.5 | 0.62 | 1.90                |
| C    | +1.5 | +7.5 | 0.60 | 1.90                |
| D    | -3.0 | +3.0 | 0.58 | 1.90                |
| E    | -3.0 | +3.0 | 0.58 | 1.90                |
| F    | -3.0 | +3.0 | 0.58 | 1.90                |

### Hypothetical Profit by Teaser Type (All Legs Win)

| Teaser Type | Legs | Std American Odds | Std Dec Odds | Stake ($) | Payout ($) | Profit ($) |
|-------------|------|-------------------|--------------|-----------|------------|------------|
| 2-leg | 2 | -135 | 1.74 | 10 | 17.40 | 7.40 |
| 3-leg | 3 | +140 | 2.40 | 10 | 24.00 | 14.00 |
| 4-leg | 4 | +240 | 3.40 | 10 | 34.00 | 24.00 |

*Std Dec Odds are converted from American odds: negative -> 1 + 100/|A|, positive -> 1 + A/100. Rounded to 2 decimals.*

**Important:** Above uses typical book standardized teaser pricing (2–4 leg focus). Your modeling (Combined_Prob, Edge, EV) should compare fair odds vs this payout schedule. Higher-leg (5–6) teasers are intentionally excluded to reduce variance and raise break-even reliability.

### Full Combination Exposure Outcomes (Uniform Stake, 2–4 Legs Only)
Assume we place EVERY possible teaser/parlay combination of the 6 picks A–F for sizes 2–4 (no 1-leg, no 5–6 leg) with a UNIFORM $10 stake on every ticket (50 tickets total):

| Size (s) | # Combos C(6,s) | Stake per Ticket ($) | Total Stake ($) | Std Dec Odds | Payout per Win ($) | Profit per Win ($) |
|----------|-----------------|----------------------|-----------------|--------------|--------------------|---------------------|
| 2 | 15 | 10 | 150 | 1.74 | 17.40 | 7.40 |
| 3 | 20 | 10 | 200 | 2.40 | 24.00 | 14.00 |
| 4 | 15 | 10 | 150 | 3.40 | 34.00 | 24.00 |
| TOTAL | 50 |  —  | 500 | — | — | — |

Total stake across all tickets = $500.

If exactly k of the 6 underlying picks win (any subset of size k), the number of winning tickets of size s is C(k,s) (0 when k < s). Total return(k) = Σ_{s=2..4} C(k,s) * (10 * dec_odds_s).

| k Winners | Winning 2L | 3L | 4L | Total Return ($) | Profit ($) | ROI (%) |
|-----------|-----------|----|----|------------------|------------|---------|
| 0 | 0 | 0 | 0 | 0.00             | -500.00    | -100.0% |
| 1 | 0 | 0 | 0 | 0.00             | -500.00    | -100.0% |
| 2 | 1 | 0 | 0 | 17.40            | -17.40     | -96.5%  |
| 3 | 3 | 1 | 0 | 76.20            | -423.80    | -84.8%  |
| 4 | 6 | 4 | 1 | 234.40           | -265.60    | -53.1%  |
| 5 | 10 | 10 | 5 | 490.00           | -10.00     | -2.0%   |
| 6 | 15 | 20 | 15 | 1251.00         | +751.00    | +150.2% |

Break-even first occurs at k = 5 (5 of 6 picks correct). Maximum upside (all 6 win) yields ≈ +150.2% ROI on total outlay.

**Formulas:**
- #Tickets size s placed: C(6,s) for s ∈ {2,3,4}
- Return(k) = Σ_{s=2..4} C(k,s) * 10 * dec_s
- Profit(k) = Return(k) − 500
- ROI(k) = Profit(k) / 500

**Notes:**
- Uniform staking: scaling stake changes $ figures linearly; ROI unchanged.
- Removing 5–6 leg tickets lowers variance and reduces reliance on perfect (6/6) outcomes; break-even still requires ≥5 wins.
- To compute expected EV, apply modeled per-pick probabilities over 64 outcome states and sum weighted profits.
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
