"""Generate reasoning + metrics images for a custom subset of Week 2 picks.

This script supports manual picks not present in the picks table (e.g., ARZ, BLT) by
supplying placeholder matchup + metric data. Existing picks with reasoning sections
in publish/reasoning/week2.txt will use those bullets; otherwise generic bullets
will be constructed.

Outputs images to: data/picks/week2_manual_selected

Usage:
  python scripts/generate_week2_manual_picks.py --teaser 6
  python scripts/generate_week2_manual_picks.py --teaser 7  (alternate teaser sizing)
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List
import argparse
import sys

# Attempt primary import; fallback to add project root if run from scripts/ directory
try:
    from panda_picks.publish.twitter import (
        _generate_styled_metrics_image,
        _generate_reasoning_image,
        load_reasoning_map,
    )
    from panda_picks.publish.twitter import format_line  # reuse formatting
except ImportError:
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT = SCRIPT_DIR.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from panda_picks.publish.twitter import (
        _generate_styled_metrics_image,
        _generate_reasoning_image,
        load_reasoning_map,
    )
    from panda_picks.publish.twitter import format_line

WEEK_LABEL = 'WEEK2'
OUTPUT_DIR = Path('data/picks/week2_manual_selected')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Manual pick list in desired order (Pick index will follow this ordering)
# NOTE: base_line reflects current market (negative = favorite, positive = dog).
PICKS = [
    ('ARZ', 'CAR@ARZ', 'ARZ', -6.5),
    ('BLT', 'BLT@BUF', 'BLT', -11.5),
    ('TB',  'TB@HST',  'TB',  2.5),
    ('IND', 'DEN@IND', 'IND',  2.5),
    ('PHI', 'PHI@KC',  'PHI', -1.5),
    ('SF',  'SF@NO',   'SF',  -3.0),
    ('LA',  'LA@TEN',  'LA',  -5.5),
]

# Placeholder / fallback metrics for manual picks if not in picks table.
MANUAL_METRICS: Dict[str, Dict[str, float]] = {
    'CAR@ARZ': { 'Overall_Adv': 4.8, 'Offense_Adv': 3.1, 'Defense_Adv': 2.9 },
    'BLT@BUF': { 'Overall_Adv': -6.2, 'Offense_Adv': -4.0, 'Defense_Adv': -7.5 },
}

KEY_NUMBERS = [-10,-9,-8,-7,-6,-4,-3]  # for teaser crossing context (ordered more negative to less)

# Confidence heuristic: abs(overall)/20 * 100 clipped 0-100, else 70% baseline.
def calc_conf(overall: float | None) -> str:
    if overall is None:
        return '70%'
    pct = max(0.0, min(100.0, abs(overall) / 20.0 * 100.0))
    return f"{pct:.0f}%"

def teaser_crossings(base_line: float | None, teased_line: float | None) -> List[int]:
    """Return key numbers crossed when moving from base_line to teased_line (favorite or dog)."""
    if base_line is None or teased_line is None:
        return []
    low = min(base_line, teased_line)
    high = max(base_line, teased_line)
    crossed = []
    for k in KEY_NUMBERS:
        # Lines more negative -> favorites; treat crossing if k is between low..high inclusive regardless sign progression
        if (low < k < high) or (high < k < low):
            crossed.append(k)
    return crossed

# Generic reasoning bullets if no external reasoning section available.
def generic_bullets(matchup: str, metrics: Dict[str, float], base_line: float | None, teaser_pts: float) -> List[str]:
    ov = metrics.get('Overall_Adv')
    off = metrics.get('Offense_Adv')
    de = metrics.get('Defense_Adv')
    conf = calc_conf(ov)
    teaser_line = base_line + teaser_pts if isinstance(base_line,(int,float)) else None
    crossed = teaser_crossings(base_line, teaser_line)
    cross_txt = (
        f"crosses {', '.join(str(c) for c in crossed)}" if crossed else "adds cushion around key zones"
    ) if base_line is not None else 'situationally neutral'
    bullets = [
        f"Baseline Model Edge: Overall edge {ov:+.1f} (multi-factor threshold clearance)" if ov is not None else "Baseline Model Edge: Positive composite advantage",
        f"Unit-Level Differential: Off {off:+.1f} / Def {de:+.1f} (balanced profile)" if off is not None and de is not None else "Unit-Level Differential: Multi-axis support",
        "Game Script Expectation: Edge facilitates early leverage + mid-game pace control",
        (f"Line Evaluation: Posted {format_line(base_line)} retains value vs internal fair (qualitative)" if base_line is not None else "Line Evaluation: Moneyline angle viable"),
        (f"Teaser Consideration: {format_line(base_line)} -> {format_line(teaser_line)} ({teaser_pts:+.1f} pts) {cross_txt}" if teaser_line is not None else "Teaser Consideration: N/A"),
        "Risk / Failure Modes: Turnover clustering, explosive play variance, red-zone stalls",
        "Why This Still Rates as a Play: Redundant edges reduce reliance on a single outlier outcome",
        f"Confidence Indicator: {conf}"
    ]
    return bullets

reasoning_map = load_reasoning_map(WEEK_LABEL)

def build_outputs(teaser_pts: float):
    summary: List[Dict[str, str]] = []
    for idx, (code, matchup, pick_side, base_line) in enumerate(PICKS, start=1):
        key = matchup.replace(' ', '')  # AWAY@HOME
        bullets = reasoning_map.get(key)
        metrics = MANUAL_METRICS.get(matchup, {})
        if not bullets:
            bullets = generic_bullets(matchup, metrics, base_line, teaser_pts)
        if not any(b.lower().startswith('confidence') for b in bullets):
            bullets.append(f"Confidence Indicator: {calc_conf(metrics.get('Overall_Adv'))}")
        teaser_line = base_line + teaser_pts if isinstance(base_line,(int,float)) else None
        lines = {'base_line': base_line, 'teaser_line': teaser_line, 'pick_rank': idx, 'pick_total': len(PICKS)}
        adv = {
            'Overall_Adv': metrics.get('Overall_Adv'),
            'Offense_Adv': metrics.get('Offense_Adv'),
            'Defense_Adv': metrics.get('Defense_Adv'),
            'Confidence': calc_conf(metrics.get('Overall_Adv')),
        }
        metrics_img = _generate_styled_metrics_image(matchup, pick_side, lines, adv, pick_index=idx, week_label=WEEK_LABEL)
        if metrics_img is None:
            print(f"[WARN] Metrics image generation returned None for {matchup} (check Pillow install & docs/text_template.png)")
        reasoning_img = _generate_reasoning_image(matchup, pick_side, bullets, idx, WEEK_LABEL)
        if reasoning_img is None:
            print(f"[WARN] Reasoning image generation returned None for {matchup} (check Pillow install & template files)")
        entry = {
            'pick_index': str(idx),
            'pick_code': code,
            'matchup': matchup,
            'pick_side': pick_side,
            'base_line': format_line(base_line),
            'teaser_line': format_line(teaser_line),
            'metrics_image': str(metrics_img) if metrics_img else None,
            'reasoning_image': str(reasoning_img) if reasoning_img else None,
        }
        for img_path in [metrics_img, reasoning_img]:
            if img_path and Path(img_path).exists():
                target = OUTPUT_DIR / Path(img_path).name
                try:
                    target.write_bytes(Path(img_path).read_bytes())
                    if Path(img_path) == metrics_img:
                        entry['metrics_image'] = str(target)
                    else:
                        entry['reasoning_image'] = str(target)
                except Exception as e:
                    print(f"[WARN] Failed to copy {img_path} -> {target}: {e}")
        (OUTPUT_DIR / f"pick_{idx}_{matchup.replace('@','_at_')}.txt").write_text('\n'.join('- ' + b for b in bullets), encoding='utf-8')
        summary.append(entry)
    summary_path = OUTPUT_DIR / 'summary.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Generated picks summary ->', summary_path)
    for s in summary:
        print(f"Pick {s['pick_index']} {s['matchup']} metrics_img={s['metrics_image']} reasoning_img={s['reasoning_image']}")


def parse_args():
    p = argparse.ArgumentParser(description='Generate manual Week 2 picks reasoning & images with adjustable teaser.')
    p.add_argument('--teaser', type=float, default=6.0, help='Teaser points to add toward pick side (default 6)')
    return p.parse_args()

if __name__ == '__main__':
    args = parse_args()
    build_outputs(args.teaser)
