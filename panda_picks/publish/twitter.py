import os
from typing import List, Dict, Any, Optional, Tuple
import logging
import tempfile
from pathlib import Path
import shutil
import re

try:
    import tweepy  # type: ignore
except Exception:  # pragma: no cover - tweepy may not be installed in some test envs
    tweepy = None  # fallback for environments without dependency installed yet

from panda_picks.data.repositories.pick_results_repository import PickResultsRepository
from panda_picks.ui.grade_utils import resolve_line_for_pick, format_line, compute_confidence
from panda_picks.ui.week_utils import week_sort_key, extract_week_number

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

# --- Brand style constants (added) ---
BRAND_NAVY = (11, 20, 36)          # #0B1424
BRAND_ORANGE = (255, 106, 26)      # #FF6A1A
BRAND_TEXT_DARK = (30, 35, 48)     # Charcoal / headline
BRAND_TEXT_MID = (70, 80, 95)
BRAND_ACCENT_GREEN = (72, 135, 43)  # existing edge bar color

_repo = PickResultsRepository()

MAX_TWEET = 280


def _get_client():
    """Create an authenticated Tweepy v2 client using env vars.
    Required env vars:
      TWITTER_API_KEY
      TWITTER_API_SECRET
      TWITTER_ACCESS_TOKEN
      TWITTER_ACCESS_SECRET
    (Optionally TWITTER_BEARER_TOKEN)
    """
    if tweepy is None:
        raise RuntimeError("tweepy not installed; run pip install tweepy")
    ak = os.getenv("TWITTER_API_KEY")
    aks = os.getenv("TWITTER_API_SECRET")
    at = os.getenv("TWITTER_ACCESS_TOKEN")
    ats = os.getenv("TWITTER_ACCESS_SECRET")
    bt = os.getenv("TWITTER_BEARER_TOKEN")
    missing = [k for k, v in {"TWITTER_API_KEY": ak, "TWITTER_API_SECRET": aks, "TWITTER_ACCESS_TOKEN": at, "TWITTER_ACCESS_SECRET": ats}.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Twitter credentials: {', '.join(missing)}")
    return tweepy.Client(consumer_key=ak, consumer_secret=aks,
                         access_token=at, access_token_secret=ats,
                         bearer_token=bt)


def _fetch_upcoming_for_week(week_label: Optional[str]) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (resolved_week_label, enriched_rows).
    If week_label is None, pick earliest week with pending (no score) games.
    """
    rows = _repo.get_upcoming_join()
    if not rows:
        return week_label or "", []
    # Organize by week
    week_to_rows: Dict[str, List[Any]] = {}
    for r in rows:
        wk = r[0]
        week_to_rows.setdefault(wk, []).append(r)
    resolved = week_label
    if resolved is None:
        # Choose smallest week number with at least one pending (scores None)
        candidate_weeks = sorted(week_to_rows.keys(), key=week_sort_key)
        for wk in candidate_weeks:
            for (_, home, away, pick_side, overall_adv, home_score, away_score, home_line, away_line) in week_to_rows[wk]:
                if home_score is None or away_score is None:  # pending
                    resolved = wk
                    break
            if resolved:
                break
        if resolved is None and candidate_weeks:
            resolved = candidate_weeks[-1]  # fallback latest
    if resolved is None:
        return "", []
    target_rows = week_to_rows.get(resolved, [])

    # Compute max abs advantage for confidence scaling (index 4)
    max_adv = max((abs(r[4]) for r in target_rows if r[4] is not None), default=1) or 1
    enriched = []
    for (wk, home, away, pick_side, overall_adv, home_score, away_score, home_line, away_line) in target_rows:
        base_line = resolve_line_for_pick(pick_side, home, away, home_line, away_line)
        predicted_pick = f"{pick_side} {format_line(base_line)}" if base_line is not None else pick_side
        spread_home = home_line if home_line is not None else (-away_line if away_line is not None else None)
        confidence = compute_confidence(overall_adv, max_adv) if overall_adv is not None else 'N/A'
        enriched.append({
            'Week': wk,
            'Home_Team': home,
            'Away_Team': away,
            'Pick_Side': pick_side,
            'Predicted_Pick': predicted_pick,
            'Overall_Adv': overall_adv,
            'Confidence': confidence,
            'Home_Line_Close': home_line,
            'Away_Line_Close': away_line,
            'Spread_Home': spread_home,
            'Base_Line': base_line,
        })
    # Keep stable ordering: by game label
    enriched.sort(key=lambda d: f"{d['Away_Team']}@{d['Home_Team']}")
    return resolved, enriched

def _fetch_pick_detail(week_label: str, home: str, away: str) -> Dict[str, Any]:
    """Fetch extended advantage details from picks table for a matchup."""
    try:
        from panda_picks.db.database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT Overall_Adv, Offense_Adv, Defense_Adv, Off_Comp_Adv, Def_Comp_Adv,
                       Home_Line_Close, Away_Line_Close, Game_Pick
                FROM picks WHERE WEEK=? AND Home_Team=? AND Away_Team=?
            """, (week_label, home, away))
            row = cur.fetchone()
            if not row:
                return {}
            return {
                'Overall_Adv': row[0], 'Offense_Adv': row[1], 'Defense_Adv': row[2],
                'Off_Comp_Adv': row[3], 'Def_Comp_Adv': row[4],
                'Home_Line_Close': row[5], 'Away_Line_Close': row[6], 'Game_Pick': row[7]
            }
    except Exception:
        return {}

def _wrap_text(draw, text: str, font, max_width: int) -> List[str]:
    """Simple word wrap returning list of lines that fit max_width."""
    if not text:
        return []
    words = text.split()
    lines: List[str] = []
    cur: List[str] = []
    for w in words:
        test = (" ".join(cur + [w])).strip()
        if draw.textlength(test, font=font) <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

def _generate_matchup_image(matchup: str, pick_side: str, lines: Dict[str, Any], adv: Dict[str, Any], narrative: Optional[str] = None, header: Optional[str] = None,
                            pick_index: Optional[int] = None, week_label: Optional[str] = None) -> Optional[Path]:
    """Generate a richer PNG card summarizing matchup metrics + narrative reasoning.
    Returns path or None if Pillow unavailable or an error occurs.
    """
    if Image is None:
        return None
    try:
        width, height = 1000, 820
        pad = 40
        bg = (248, 248, 250)
        panel_bg = (235, 238, 241)
        img = Image.new('RGB', (width, height), bg)
        draw = ImageDraw.Draw(img)
        # Fonts
        try:
            font_title = ImageFont.truetype('arial.ttf', 50)
            font_h2 = ImageFont.truetype('arial.ttf', 38)
            font_body = ImageFont.truetype('arial.ttf', 26)
            font_small = ImageFont.truetype('arial.ttf', 22)
        except Exception:
            font_title = font_h2 = font_body = font_small = ImageFont.load_default()
        y = pad
        # Header
        hdr = header or (f"Dick Picks Week {extract_week_number(week_label) or ''}" if week_label else "Dick Picks")
        if pick_index is not None:
            hdr = f"{hdr} - Pick {pick_index}"
        draw.text((pad, y), hdr, fill=(30, 55, 90), font=font_title)
        y += 70
        # Matchup & Pick
        draw.text((pad, y), matchup, fill=(25, 25, 25), font=font_h2)
        y += 50
        draw.text((pad, y), f"Pick: {pick_side}", fill=(0, 110, 0), font=font_body)
        y += 40
        base_line = lines.get('base_line')
        teaser_line = lines.get('teaser_line')
        draw.text((pad, y), f"Line {format_line(base_line)}  |  Teaser {format_line(teaser_line)}", fill=(20,60,120), font=font_body)
        y += 46
        # Metrics panel
        panel_top = y
        panel_left = pad
        panel_width = width - pad*2
        panel_height = 160
        draw.rectangle([panel_left, panel_top, panel_left+panel_width, panel_top+panel_height], fill=panel_bg)
        inner_y = panel_top + 16
        metric_cols = [
            ('Overall_Adv', 'Overall'), ('Offense_Adv','Off'), ('Defense_Adv','Def'),
            ('Off_Comp_Adv','OffCmp'), ('Def_Comp_Adv','DefCmp')
        ]
        x_cursor = panel_left + 20
        for key,label in metric_cols:
            val = adv.get(key)
            if val is None:
                continue
            txt = f"{label}: {val:+.1f}"
            draw.text((x_cursor, inner_y), txt, fill=(40,40,40), font=font_body)
            inner_y += 34
            if inner_y > panel_top + panel_height - 34:
                # move to next column
                inner_y = panel_top + 16
                x_cursor += 170
        # Overall edge bar
        overall = adv.get('Overall_Adv')
        if isinstance(overall, (int,float)):
            bar_y = panel_top + panel_height - 40
            bar_x = panel_left + 20
            bar_w = panel_width - 40
            bar_h = 24
            draw.rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], fill=(220,220,220))
            scaled = max(min(overall, 20), -20)  # clamp
            frac = (scaled + 20)/40.0
            fill_w = int(bar_w * frac)
            draw.rectangle([bar_x, bar_y, bar_x+fill_w, bar_y+bar_h], fill=(72,135,43))
            draw.text((bar_x, bar_y-26), 'Overall Edge (scaled ±20)', fill=(55,55,55), font=font_small)
        y = panel_top + panel_height + 30
        # Narrative reasoning section
        narrative = (narrative or '').strip()
        if narrative:
            draw.text((pad, y), "Why this pick:", fill=(30,55,90), font=font_h2)
            y += 48
            # Split narrative into pseudo sentences for bullets
            sentences: List[str] = []
            raw_sent = narrative.replace('\n', ' ').split('. ')
            for seg in raw_sent:
                seg = seg.strip().strip('.')
                if seg:
                    sentences.append(seg)
            # Wrap each sentence separately
            max_text_width = width - pad*2 - 40
            bullet_y = y
            max_bullets = 6
            for i, seg in enumerate(sentences[:max_bullets]):
                wrapped = _wrap_text(draw, seg, font_body, max_text_width)
                if not wrapped:
                    continue
                # First line with bullet
                first_line = wrapped[0]
                draw.text((pad+10, bullet_y), f"• {first_line}", fill=(25,25,25), font=font_body)
                bullet_y += 32
                for cont in wrapped[1:]:
                    draw.text((pad+40, bullet_y), cont, fill=(25,25,25), font=font_body)
                    bullet_y += 32
                if bullet_y > height - 60:
                    break
            y = bullet_y + 10
        # Branding footer
        footer = "Panda Picks - Model driven insights"
        draw.text((pad, height-50), footer, fill=(90,90,90), font=font_small)
        tmp_dir = Path(tempfile.mkdtemp(prefix='dickpicks_'))
        out_path = tmp_dir / (matchup.replace(' ','_').replace('@','_at_') + '.png')
        img.save(out_path)
        return out_path
    except Exception as e:  # pragma: no cover
        logging.error(f"Image generation failed: {e}")
        return None

# Expanded reasoning helper
from panda_picks.config.settings import Settings

KEY_NUMBERS = [-3, -4, -6, -7]

def _build_expanded_reasoning(overall: Optional[float], off_adv: Optional[float], def_adv: Optional[float],
                               base_line: Optional[float], teaser_line: Optional[float], confidence: Optional[str]) -> List[str]:
    bullets: List[str] = []
    # Baseline Model Edge
    if overall is not None:
        thresh = Settings.ADVANTAGE_THRESHOLDS.get('Overall_Adv', 2.0)
        bullets.append(f"Baseline Model Edge: Overall edge {overall:+.1f} vs threshold {thresh:.1f} (strong conviction zone)" )
    else:
        bullets.append("Baseline Model Edge: Valid multi-signal advantage present")
    # Unit-Level Differential
    if off_adv is not None or def_adv is not None:
        if off_adv is not None and def_adv is not None:
            primary = 'Offense' if abs(off_adv) > abs(def_adv) else 'Defense'
            bullets.append(f"Unit-Level Differential: {primary} leads (Off {off_adv:+.1f} / Def {def_adv:+.1f}) supporting sustainable script")
        elif off_adv is not None:
            bullets.append(f"Unit-Level Differential: Offense edge {off_adv:+.1f} drives projection")
        else:
            bullets.append(f"Unit-Level Differential: Defense edge {def_adv:+.1f} drives projection")
    # Game Script Expectation
    if def_adv is not None and (off_adv is None or abs(def_adv) >= abs(off_adv)):
        bullets.append("Game Script Expectation: Defensive disruption generates short fields / stalled opponent drives enabling early control")
    else:
        bullets.append("Game Script Expectation: Offensive efficiency sustains drives and pressures opponent pace adjustments")
    # Line Evaluation
    if base_line is not None and overall is not None:
        # heuristic fair line estimate: translate overall edge to spread delta ~ edge/2
        fair = (base_line if base_line <= 0 else -base_line) - (overall/2.0 if base_line <=0 else -(overall/2.0))
        cushion = fair - base_line
        bullets.append(f"Line Evaluation: Posted {format_line(base_line)} vs fair est {format_line(round(fair,1))} (cushion {cushion:+.1f} pts)")
    elif base_line is not None:
        bullets.append(f"Line Evaluation: Posted {format_line(base_line)} remains within playable band")
    else:
        bullets.append("Line Evaluation: Moneyline value (no reliable spread input)")
    # Teaser Consideration
    if base_line is not None and teaser_line is not None:
        crossed = [k for k in KEY_NUMBERS if (base_line < k < teaser_line) or (teaser_line < k < base_line)] if base_line < 0 else []
        if base_line < 0:
            bullets.append(f"Teaser Consideration: {format_line(base_line)} -> {format_line(teaser_line)} crosses {', '.join(map(str,crossed)) if crossed else 'key values'}")
        else:
            bullets.append("Teaser Consideration: Less optimal (not moving through premium numbers)")
    # Risk / Failure Modes
    bullets.append("Risk / Failure Modes: Explosive plays variance, turnover delta, special teams field position swing, late game variance")
    # Why Still Play
    bullets.append("Why This Still Rates as a Play: Multi-factor edge (macro + unit) with structural, not single fragile signal")
    # Confidence
    if confidence and confidence != 'N/A':
        bullets.append(f"Pick Strength: {confidence}")
    return bullets

# Separate image generation: metrics + reasoning

# --- NEW: Styled metrics image using provided template ---

def _locate_white_panel(im: 'Image.Image'):
    """Attempt to locate the primary white/light panel region in the template.
    Returns (left, top, right, bottom) or None if detection fails.
    Heuristic: collect all pixels with min(rgb) > 235 & alpha > 200, compute their bounding box,
    then ensure region area is a reasonable fraction of image ( >25%).
    """
    try:
        px = im.load()
        w, h = im.size
        min_x = w; min_y = h; max_x = 0; max_y = 0; count = 0
        # sample with stride for speed
        stride = max(1, int(min(w, h)/400))
        for y in range(0, h, stride):
            for x in range(0, w, stride):
                r, g, b, *rest = px[x, y] if len(px[x, y]) >= 3 else (*px[x, y], 255)
                a = rest[0] if rest else 255
                if a > 200 and min(r, g, b) > 235:  # bright pixel
                    count += 1
                    if x < min_x: min_x = x
                    if y < min_y: min_y = y
                    if x > max_x: max_x = x
                    if y > max_y: max_y = y
        if count == 0:
            return None
        # sanity checks
        area = (max_x - min_x) * (max_y - min_y)
        if area < (w * h * 0.20):  # too small to be main panel
            return None
        # add small insets to avoid borders
        inset = 8
        min_x = max(0, min_x + inset)
        min_y = max(0, min_y + inset)
        max_x = min(w, max_x - inset)
        max_y = min(h, max_y - inset)
        return (min_x, min_y, max_x, max_y)
    except Exception:
        return None

def _draw_metric_pair(draw: 'ImageDraw.ImageDraw', label: str, value: float | None, x: int, y: int, label_font, value_font, color=BRAND_TEXT_DARK) -> int:
    if value is None:
        txt = f"{label}: --"
    else:
        txt = f"{label}: {value:+.1f}"
    draw.text((x, y), txt, fill=color, font=label_font)
    return y + int(label_font.size * 1.15)

def _styled_metrics_layout(d: 'ImageDraw.ImageDraw', panel_box: tuple, header_data: dict, adv: dict, fonts: dict):
    """Render metrics inside the white panel matching latest sample design.

    Updated: Removed explicit tag bar (template already contains branding) and removed composite metrics.
    Display order now: Overall, Offense, Defense only. Vertically centered within panel.
    Added: Pick Strength bar visualization (0-100) and slight extra spacing before it.
    Refined: Content shifted slightly downward; Pick Strength bar width reduced (~72% of available width).
    """
    left, top, right, bottom = panel_box
    inner_pad = 46
    x = left + inner_pad
    panel_height = bottom - top

    h2_h = fonts['h2'].size
    body_h = fonts['body'].size
    row_h = body_h + 6
    spacing_before_strength = 14
    bar_h = 18
    bar_gap_above = 6

    content_height = (h2_h + 10) + (body_h + 18) + 18 + (h2_h + 10) + (row_h * 3) + 6 + spacing_before_strength + h2_h + bar_gap_above + bar_h
    min_top_pad = 28
    dynamic_top_offset = max(min_top_pad, int((panel_height - content_height) / 2))
    extra_shift = 10  # bump everything down a hair
    y = top + dynamic_top_offset + extra_shift

    # Matchup line
    matchup = header_data['matchup'].replace('@', ' @ ')
    d.text((x, y), matchup, fill=BRAND_TEXT_DARK, font=fonts['h2'])
    y += h2_h + 10

    # Pick / line line
    base_line = header_data.get('base_line')
    teaser_line = header_data.get('teaser_line')
    pick_line = header_data['pick_side']
    line_txt = f"Pick: {pick_line} | Line {format_line(base_line)} | Teaser {format_line(teaser_line)}"
    d.text((x, y), line_txt, fill=BRAND_TEXT_MID, font=fonts['body'])
    y += body_h + 18

    # Divider
    d.line([x, y, right - inner_pad, y], fill=(210,213,218), width=1)
    y += 18

    # Section header
    d.text((x, y), 'Advantage Analysis', fill=BRAND_TEXT_DARK, font=fonts['h2'])
    y += h2_h + 10

    # Metrics list (only primary three metrics)
    metrics_order = [
        ('Overall', adv.get('Overall_Adv')),
        ('Offense', adv.get('Offense_Adv')),
        ('Defense', adv.get('Defense_Adv')),
    ]
    label_color = BRAND_TEXT_DARK
    value_color = BRAND_NAVY

    for label, val in metrics_order:
        label_txt = f"{label}:"
        d.text((x, y), label_txt, fill=label_color, font=fonts['body'])
        val_txt = ''
        if isinstance(val, (int, float)):
            val_txt = f"{val:+.1f}"
        label_col_w = 220
        vx = x + label_col_w
        d.text((vx, y), val_txt, fill=value_color, font=fonts['body'])
        y += row_h

    y += 6 + spacing_before_strength
    # Pick Strength label + bar
    confidence_raw = header_data.get('confidence')
    pct_val: Optional[float] = None
    if isinstance(confidence_raw, str) and confidence_raw.endswith('%'):
        try:
            pct_val = max(0.0, min(100.0, float(confidence_raw[:-1])))
        except Exception:
            pct_val = None
    elif isinstance(confidence_raw, (int, float)):
        pct_val = max(0.0, min(100.0, float(confidence_raw)))

    # Label text (show numeric if available)
    strength_display = f"{int(round(pct_val))}/100" if pct_val is not None else ''
    # Append rank if available
    rank_part = ''
    pr = header_data.get('pick_rank')
    pt = header_data.get('pick_total')
    if isinstance(pr,int) and isinstance(pt,int) and pt>0:
        rank_part = f"  (# {pr} of {pt})"
    d.text((x, y), f"Pick Strength: {strength_display}{rank_part}", fill=BRAND_TEXT_DARK, font=fonts['h2'])
    y += h2_h + bar_gap_above

    # Draw bar if we have a percentage
    if pct_val is not None:
        total_available = (right - inner_pad) - x
        bar_width = int(total_available * 0.72)  # shorten bar
        bar_left = x
        bar_right = bar_left + bar_width
        bar_top = y
        bar_bottom = bar_top + bar_h
        # Background
        d.rounded_rectangle([bar_left, bar_top, bar_right, bar_bottom], radius=6, fill=(225,228,231))
        fill_frac = pct_val / 100.0
        if fill_frac > 0:
            fill_w = int(bar_width * fill_frac)
            d.rounded_rectangle([bar_left, bar_top, bar_left + fill_w, bar_bottom], radius=6, fill=BRAND_ACCENT_GREEN)
        # Optional center marker (50%)
        mid_x = bar_left + bar_width // 2
        d.line([mid_x, bar_top, mid_x, bar_bottom], fill=(255,255,255,140), width=1)

def _generate_styled_metrics_image(matchup: str, pick_side: str, lines: Dict[str, Any], adv: Dict[str, Any], pick_index: int, week_label: Optional[str], template_path: Optional[str] = None) -> Optional[Path]:
    """Generate a metrics card using the branded template (with white panel) if available.
    Falls back to legacy _generate_metrics_image on failure.
    """
    if Image is None:
        return None
    # Resolve template path default
    search_candidates: List[Path] = []
    if template_path:
        search_candidates.append(Path(template_path))
    # repo relative docs/
    search_candidates.append(Path(__file__).resolve().parent.parent.parent / 'docs' / 'text_template.png')
    search_candidates.append(Path(__file__).resolve().parent.parent.parent / 'docs' / 'text_template_plain.png')
    tpl = None
    for c in search_candidates:
        if c.exists():
            tpl = c
            break
    if tpl is None:
        # fallback legacy
        return _generate_metrics_image(matchup, pick_side, lines, adv, pick_index, week_label)
    try:
        base = Image.open(tpl).convert('RGBA')
        panel_box = _locate_white_panel(base)
        if not panel_box:
            # fallback static box: assume 60px margin
            w, h = base.size
            panel_box = (60, 120, w - 60, h - 60)
        # Draw overlay on copy
        out = base.copy()
        draw = ImageDraw.Draw(out)
        # Fonts
        try:
            font_title = ImageFont.truetype('arial.ttf', 46)
            font_h2 = ImageFont.truetype('arial.ttf', 34)
            font_body = ImageFont.truetype('arial.ttf', 24)
            font_small = ImageFont.truetype('arial.ttf', 18)
        except Exception:
            font_title = font_h2 = font_body = font_small = ImageFont.load_default()
        wk_num = extract_week_number(week_label) or ''
        header_data = {
            'matchup': matchup,
            'pick_side': pick_side,
            'base_line': lines.get('base_line'),
            'teaser_line': lines.get('teaser_line'),
            'pick_index': pick_index,
            'week_num': wk_num,
            'confidence': adv.get('Confidence'),  # new
            'pick_rank': lines.get('pick_rank'),
            'pick_total': lines.get('pick_total'),
        }
        _styled_metrics_layout(draw, panel_box, header_data, adv, {
            'title': font_title,
            'h2': font_h2,
            'body': font_body,
            'small': font_small
        })
        # Save
        tmp_dir = Path(tempfile.mkdtemp(prefix='styled_metrics_'))
        out_path = tmp_dir / (matchup.replace(' ','_').replace('@','_at_') + '_styled_metrics.png')
        out.save(out_path)
        return out_path
    except Exception:
        return _generate_metrics_image(matchup, pick_side, lines, adv, pick_index, week_label)


def _generate_metrics_image(matchup: str, pick_side: str, lines: Dict[str, Any], adv: Dict[str, Any],
                             pick_index: int, week_label: Optional[str]) -> Optional[Path]:
    if Image is None:
        return None
    try:
        width, height = 1000, 420
        pad = 30
        img = Image.new('RGB', (width, height), (255,255,255))
        d = ImageDraw.Draw(img)
        try:
            f_title = ImageFont.truetype('arial.ttf', 42)
            f_h2 = ImageFont.truetype('arial.ttf', 30)
            f_body = ImageFont.truetype('arial.ttf', 24)
        except Exception:
            f_title = f_h2 = f_body = ImageFont.load_default()
        y = pad
        wk_num = extract_week_number(week_label) or ''
        d.text((pad,y), f"Week {wk_num} – Pick {pick_index}", fill=(15,40,80), font=f_title)
        y+=60
        d.text((pad,y), matchup.replace('@',' @ '), fill=(0,0,0), font=f_h2); y+=40
        d.text((pad,y), f"Pick: {pick_side}", fill=(0,100,0), font=f_body); y+=30
        base_line = lines.get('base_line'); teaser_line = lines.get('teaser_line')
        d.text((pad,y), f"Line {format_line(base_line)} | Teaser {format_line(teaser_line)}", fill=(20,60,120), font=f_body); y+=20
        # Metrics panel box
        panel_y = y+14
        panel_h = 200
        d.rectangle([pad, panel_y, width-pad, panel_y+panel_h], outline=(0,0,0), fill=(238,238,240))
        inner_y = panel_y + 15
        metrics = []
        ov = adv.get('Overall_Adv'); off = adv.get('Offense_Adv'); de = adv.get('Defense_Adv')
        if ov is not None:
            metrics.append((f"Overall: {ov:+.1f}", ''))
        if off is not None:
            metrics.append((f"Offense: {off:+.1f}", ''))
        if de is not None:
            metrics.append((f"Defense: {de:+.1f}", ''))
        for m,_ in metrics:
            d.text((pad+12, inner_y), m, fill=(25,25,25), font=f_body)
            inner_y += 34
        # Edge bar
        if ov is not None:
            bar_w = width - pad*2 - 40
            bar_x = pad+12
            bar_y = panel_y + panel_h - 45
            d.rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+26], fill=(230,230,230))
            scaled = max(min(ov,20),-20)
            frac = (scaled+20)/40
            fill_w = int(bar_w*frac)
            d.rectangle([bar_x, bar_y, bar_x+fill_w, bar_y+26], fill=(72,135,43))
            d.text((bar_x, bar_y-24), 'Overall Edge (±20 scaled)', fill=(55,55,55), font=f_body)
        tmp = Path(tempfile.mkdtemp(prefix='metrics_'))
        out = tmp / (matchup.replace(' ','_').replace('@','_at_') + '_metrics.png')
        img.save(out)
        return out
    except Exception:
        return None


def _generate_reasoning_image(matchup: str, pick_side: str, bullets: List[str], pick_index: int, week_label: Optional[str]) -> Optional[Path]:
    if Image is None:
        return None
    try:
        # Try to load branded reasoning template first
        tpl_candidates: List[Path] = [
            Path(__file__).resolve().parent.parent.parent / 'docs' / 'reasoning_template.png',
            Path(__file__).resolve().parent.parent.parent / 'docs' / 'text_template.png',  # fallback alt
        ]
        template_path: Optional[Path] = None
        for c in tpl_candidates:
            if c.exists():
                template_path = c
                break
        # Helper to load Inter font (body 14pt, title 20pt) with fallback
        def _load_inter_fonts():
            font_candidates = [
                'Inter-Regular.ttf', 'Inter.ttf',
                str(Path.cwd() / 'Inter-Regular.ttf'),
                '/usr/share/fonts/truetype/inter/Inter-Regular.ttf',
                '/Library/Fonts/Inter-Regular.ttf',
                'C:/Windows/Fonts/Inter-Regular.ttf'
            ]
            body = None; title = None
            for pth in font_candidates:
                try:
                    body = ImageFont.truetype(pth, 16)
                    title = ImageFont.truetype(pth, 24)
                    break
                except Exception:
                    continue
            if body is None:
                try:
                    body = ImageFont.truetype('arial.ttf', 16)
                    title = ImageFont.truetype('arial.ttf', 24)
                except Exception:
                    body = title = ImageFont.load_default()
            return title, body
        # --- New helper for bold prefix drawing ---
        def _draw_bold(draw: 'ImageDraw.ImageDraw', xy: Tuple[int,int], text: str, font, fill):
            # Simulate bold by drawing text multiple times with tiny offsets
            x, y = xy
            for dx, dy in ((0,0),(1,0),(0,1),(1,1)):
                draw.text((x+dx, y+dy), text, font=font, fill=fill)
        def _wrap_bullet_with_prefix(draw: 'ImageDraw.ImageDraw', prefix: str, remainder: str, font, max_width: int) -> List[str]:
            """Custom wrap so first line accounts for prefix width. Returns list of lines (first begins with remainder part only)."""
            if not remainder:
                return [""]
            words = remainder.split()
            lines: List[str] = []
            cur: List[str] = []
            # width available for first line (prefix already occupies space). We'll compute outside.
            # Here we just produce wrapped lines for remainder full width; caller may pre-wrap differently if needed.
            for w in words:
                test = (" ".join(cur + [w])).strip()
                if draw.textlength(test, font=font) <= max_width or not cur:
                    cur.append(w)
                else:
                    lines.append(" ".join(cur))
                    cur = [w]
            if cur:
                lines.append(" ".join(cur))
            return lines
        if template_path:
            base = Image.open(template_path).convert('RGBA')
            panel_box = _locate_white_panel(base)
            if not panel_box:
                # manual heuristic: assume 60px left/right margin & top 65, bottom 120 (leaving footer art)
                w, h = base.size
                panel_box = (60, 70, w - 60, h - 120)
            left, top, right, bottom = panel_box
            # Adjust bottom to avoid panda watermark (reserve 140px near base if logo detected)
            w, h = base.size
            safe_bottom = min(bottom, h - 150)
            bottom = safe_bottom if safe_bottom - top > 200 else bottom
            out = base.copy()
            draw = ImageDraw.Draw(out)
            title_font, body_font = _load_inter_fonts()
            # Derive display matchup title (ensure spaced @)
            display_matchup = matchup
            if '@' in matchup and ' @ ' not in matchup:
                parts = matchup.split('@')
                if len(parts) == 2:
                    display_matchup = parts[0].strip() + ' @ ' + parts[1].strip()
            # Header lines
            header = display_matchup
            sub_header = f"Why this pick? – Pick {pick_index}" if pick_index else "Why this pick?"
            inner_pad_x = 32
            inner_pad_y = 28
            x = left + inner_pad_x
            y = top + inner_pad_y
            draw.text((x, y), header, fill=BRAND_TEXT_DARK, font=title_font)
            y += title_font.size + 6
            draw.text((x, y), sub_header, fill=BRAND_TEXT_MID, font=body_font)
            y += body_font.size + 14
            # Prepare wrapped bullets with Inter body font 14pt
            max_width = right - inner_pad_x - x - 10
            line_height = int(body_font.size * 1.55)
            bullet_gap = 4
            for b in bullets:
                # Split prefix
                prefix = None
                remainder = b
                if ':' in b:
                    pre, rem = b.split(':', 1)
                    if pre.strip():
                        prefix = pre.strip() + ':'
                        remainder = rem.strip()
                if prefix:
                    # Width remaining for first line after bullet + space + prefix + space
                    bullet_prefix = '• '
                    prefix_width = draw.textlength(bullet_prefix + prefix + ' ', font=body_font)
                    available_first = max(10, max_width - prefix_width)
                    rem_lines = _wrap_bullet_with_prefix(draw, prefix, remainder, body_font, available_first)
                    if not rem_lines:
                        rem_lines = ['']
                    # Draw first line
                    line_y = y
                    # Bullet + bold prefix
                    draw.text((x, line_y), bullet_prefix, fill=BRAND_TEXT_DARK, font=body_font)
                    _draw_bold(draw, (x + int(draw.textlength(bullet_prefix, font=body_font)), line_y), prefix, body_font, BRAND_TEXT_DARK)
                    # Remainder of first line
                    rx = x + int(prefix_width)
                    draw.text((rx, line_y), rem_lines[0], fill=BRAND_TEXT_DARK, font=body_font)
                    y += line_height
                    # Subsequent lines
                    for ln in rem_lines[1:]:
                        draw.text((x + int(draw.textlength(bullet_prefix, font=body_font)), y), ln, fill=BRAND_TEXT_DARK, font=body_font)
                        y += line_height
                else:
                    wrapped = _wrap_text(draw, b, body_font, max_width)
                    first = True
                    for ln in wrapped:
                        prefix_sym = '• ' if first else '  '
                        draw.text((x, y), prefix_sym + ln, fill=BRAND_TEXT_DARK, font=body_font)
                        y += line_height
                        first = False
                y += bullet_gap
                if y > bottom - line_height:
                    if y <= bottom - line_height/2:
                        draw.text((x, y), '…', fill=BRAND_TEXT_DARK, font=body_font)
                    break
            tmp = Path(tempfile.mkdtemp(prefix='reason_tpl_'))
            out_path = tmp / (display_matchup.replace(' ','_').replace('@','_at_') + '_reason.png')
            out.save(out_path)
            return out_path
        # Fallback legacy plain style (Inter 14pt if possible)
        width, height = 1200, 1000
        pad = 35
        img = Image.new('RGB', (width, height), (255,255,255))
        d = ImageDraw.Draw(img)
        title_font, body_font = _load_inter_fonts()
        y = pad
        # Display matchup & header
        display_matchup = matchup
        if '@' in matchup and ' @ ' not in matchup:
            parts = matchup.split('@')
            if len(parts) == 2:
                display_matchup = parts[0].strip() + ' @ ' + parts[1].strip()
        d.text((pad, y), display_matchup, fill=BRAND_TEXT_DARK, font=title_font); y += title_font.size + 6
        sub_header = f"Why this pick? – Pick {pick_index}" if pick_index else "Why this pick?"
        d.text((pad, y), sub_header, fill=BRAND_TEXT_MID, font=body_font); y += body_font.size + 14
        maxw = width - 2*pad - 60
        line_height = int(body_font.size * 1.55)
        bullet_gap = 4
        for b in bullets:
            prefix = None
            remainder = b
            if ':' in b:
                pre, rem = b.split(':', 1)
                if pre.strip():
                    prefix = pre.strip() + ':'
                    remainder = rem.strip()
            if prefix:
                bullet_prefix = '• '
                prefix_width = d.textlength(bullet_prefix + prefix + ' ', font=body_font)
                available_first = max(10, maxw - prefix_width)
                rem_lines = _wrap_bullet_with_prefix(d, prefix, remainder, body_font, available_first)
                if not rem_lines:
                    rem_lines = ['']
                line_y = y
                d.text((pad, line_y), bullet_prefix, fill=BRAND_TEXT_DARK, font=body_font)
                _draw_bold(d, (pad + int(d.textlength(bullet_prefix, font=body_font)), line_y), prefix, body_font, BRAND_TEXT_DARK)
                rx = pad + int(prefix_width)
                d.text((rx, line_y), rem_lines[0], fill=BRAND_TEXT_DARK, font=body_font)
                y += line_height
                for ln in rem_lines[1:]:
                    d.text((pad + int(d.textlength(bullet_prefix, font=body_font)), y), ln, fill=BRAND_TEXT_DARK, font=body_font)
                    y += line_height
            else:
                lines = _wrap_text(d, b, body_font, maxw)
                if not lines:
                    continue
                first = True
                for ln in lines:
                    prefix_sym = '• ' if first else '  '
                    d.text((pad, y), prefix_sym + ln, fill=BRAND_TEXT_DARK, font=body_font)
                    y += line_height
                    first = False
            y += bullet_gap
            if y > height - 90:
                if y <= height - 70:
                    d.text((pad, y), '…', fill=BRAND_TEXT_DARK, font=body_font)
                break
        footer = "Panda Picks - Model driven insights"
        d.text((pad, height-50), footer, fill=(120,120,120), font=body_font)
        tmp = Path(tempfile.mkdtemp(prefix='reason_'))
        out = tmp / (display_matchup.replace(' ','_').replace('@','_at_') + '_reason.png')
        img.save(out)
        return out
    except Exception:
        return None

REASONING_DIR = Path(__file__).resolve().parent / 'reasoning'
REASONING_DIR.mkdir(parents=True, exist_ok=True)

def _reasoning_file_for_week(week_label: str) -> Path:
    wk_num = extract_week_number(week_label)
    if wk_num is None:
        return REASONING_DIR / 'week_unknown.txt'
    return REASONING_DIR / f'week{wk_num}.txt'

def load_reasoning_map(week_label: str) -> Dict[str, List[str]]:
    """Load external reasoning bullets from a text file if present.
    Expected format per pick section:
    ## Week 1 – Pick 1: AWAY @ HOME
    - Baseline Model Edge: ...
    - Unit-Level Differential: ...
    Blank line separates sections.
    Returns dict keyed by 'AWAY@HOME'."""
    path = _reasoning_file_for_week(week_label)
    if not path.exists():
        return {}
    try:
        content = path.read_text(encoding='utf-8')
    except Exception:
        return {}
    sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
    reasoning: Dict[str, List[str]] = {}
    for sec in sections:
        sec = sec.strip()
        if not sec or not sec.lower().startswith('week'):
            continue
        header_line, *rest = sec.splitlines()
        # Extract matchup after colon
        m = re.search(r':\s*([^\n]+)', header_line)
        matchup_raw = m.group(1).strip() if m else ''
        matchup_norm = matchup_raw.replace(' ', '')  # remove spaces around @
        matchup_norm = matchup_norm.replace('@', '@')
        bullets: List[str] = []
        for line in rest:
            if line.strip().startswith('- '):
                bullets.append(line.strip()[2:].strip())
        if matchup_raw and bullets:
            key = matchup_raw.replace(' ', '')  # AWAY@HOME
            reasoning[key] = bullets
    return reasoning

def build_dick_picks_thread(week_label: Optional[str] = None, teaser_adjust: float = 6.0,
                            include_images: bool = True, blurb_char_limit: int = 200) -> List[Dict[str, Any]]:
    """Return list of tweet payload dicts in the Dick Picks format.

    Tweet 1: "Here are your Dick Picks for week X!" followed by enumerated list of picks with base & teaser lines.
    Tweet 2-n: One tweet per pick: "Pick N: AWAY@HOME" + <= blurb_char_limit reasoning + optional image.
    Splits summary across multiple tweets if necessary (rare) while preserving ordering.
    """
    resolved_week, picks = _fetch_upcoming_for_week(week_label)
    if not picks:
        return []
    # Compute ranking by absolute overall advantage (higher first)
    overall_list = []
    for p in picks:
        ov = p.get('Overall_Adv')
        if isinstance(ov,(int,float)):
            overall_list.append((abs(ov), p['Away_Team'], p['Home_Team']))
    overall_list.sort(reverse=True, key=lambda x: x[0])
    rank_map = {}
    total_picks = len(overall_list)
    for idx,(val, away_t, home_t) in enumerate(overall_list, start=1):
        key = f"{away_t}@{home_t}".replace(' ','')
        rank_map[key] = (idx, total_picks)
    week_num = extract_week_number(resolved_week)
    wk_disp = f"week {week_num}" if week_num is not None else resolved_week

    # Build summary lines enumerated.
    summary_lines: List[str] = []
    for i, p in enumerate(picks, start=1):
        base_line = p.get('Base_Line')
        teaser_line = base_line + teaser_adjust if base_line is not None else None
        line_part = format_line(base_line) if base_line is not None else 'ML'
        teaser_part = format_line(teaser_line) if teaser_line is not None else 'ML'
        summary_lines.append(f"{i}) {p['Pick_Side']} {line_part} (Teaser {teaser_part})")

    # Flashy multi-line header with emojis/icons
    flashy_header_lines = [
        f"🚀🏈 Panda Picks {wk_disp.title()} 🏈🚀",
        "⚡ Top Model Edge Plays Locked In ⚡",
        "Ranked by confidence ↓"
    ]
    header = "\n".join(flashy_header_lines)
    # Pack summary lines into as few tweets as possible.
    summary_tweets: List[str] = []
    current_block: List[str] = []
    for line in summary_lines:
        candidate = header + "\n" + "\n".join(current_block + [line]) if not summary_tweets else "\n".join(current_block + [line])
        if len(candidate) > MAX_TWEET:
            # finalize current block
            if not current_block:  # single long line fallback truncate
                truncated = (line[:MAX_TWEET-3] + '...') if len(line) > MAX_TWEET else line
                if not summary_tweets:
                    summary_tweets.append(header + "\n" + truncated)
                else:
                    summary_tweets.append(truncated)
                continue
            # push block
            if not summary_tweets:
                summary_tweets.append(header + "\n" + "\n".join(current_block))
            else:
                summary_tweets.append("\n".join(current_block))
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        if not summary_tweets:
            summary_tweets.append(header + "\n" + "\n".join(current_block))
        else:
            summary_tweets.append("\n".join(current_block))
    # Add continuation marker if multiple summary tweets
    if len(summary_tweets) > 1:
        for idx in range(1, len(summary_tweets)):
            cont_tag = f"(cont. {idx+1}/{len(summary_tweets)})"
            if len(summary_tweets[idx] + "\n" + cont_tag) <= MAX_TWEET:
                summary_tweets[idx] = summary_tweets[idx] + "\n" + cont_tag

    tweet_payloads: List[Dict[str, Any]] = []
    for t in summary_tweets:
        tweet_payloads.append({'text': t, 'image_path': None, 'image_paths': []})

    # Detailed pick tweets
    reasoning_map = load_reasoning_map(resolved_week)
    for idx, p in enumerate(picks, start=1):
        home = p['Home_Team']; away = p['Away_Team']; pick_side = p['Pick_Side']
        matchup_key = f"{away}@{home}".replace(' ', '')
        matchup = f"{away}@{home}"  # no spaces
        adv_detail = _fetch_pick_detail(p['Week'], home, away)
        overall = adv_detail.get('Overall_Adv', p.get('Overall_Adv'))
        off_adv = adv_detail.get('Offense_Adv')
        def_adv = adv_detail.get('Defense_Adv')
        off_comp = adv_detail.get('Off_Comp_Adv')
        def_comp = adv_detail.get('Def_Comp_Adv')
        base_line = p.get('Base_Line')
        teaser_line = base_line + teaser_adjust if base_line is not None else None
        confidence = p.get('Confidence')
        # External reasoning override
        external_bullets = reasoning_map.get(matchup_key)
        if external_bullets:
            bullets = external_bullets
        else:
            bullets = _build_expanded_reasoning(overall, off_adv, def_adv, base_line, teaser_line, confidence)
        # Prepare adv dict for card with confidence
        adv_for_card = dict(adv_detail) if adv_detail else {'Overall_Adv': overall}
        if confidence and 'Confidence' not in adv_for_card:
            adv_for_card['Confidence'] = confidence
        # Short tweet blurb first bullet
        primary_blurb = bullets[0] if bullets else 'Model value vs market'
        if len(primary_blurb) > blurb_char_limit:
            primary_blurb = primary_blurb[:blurb_char_limit-3] + '...'
        header_line = f"Pick {idx}: {matchup}"
        remaining_allowed = MAX_TWEET - len(header_line) - 1
        if len(primary_blurb) > remaining_allowed:
            primary_blurb = primary_blurb[:remaining_allowed-3] + '...'
        tweet_text = header_line + "\n" + primary_blurb
        image_paths: List[str] = []
        if include_images:
            # NEW: try styled template metrics image first
            # add rank info into lines dict for header_data
            rinfo = rank_map.get(matchup_key)
            rank_lines = {'base_line': base_line,'teaser_line': teaser_line}
            if rinfo:
                rank_lines['pick_rank'] = rinfo[0]
                rank_lines['pick_total'] = rinfo[1]
            metrics_img = _generate_styled_metrics_image(matchup, pick_side, rank_lines, adv_for_card if adv_for_card else {'Overall_Adv': overall}, idx, p['Week'])
            if metrics_img is None:
                metrics_img = _generate_metrics_image(matchup, pick_side, {'base_line': base_line,'teaser_line': teaser_line}, adv_for_card if adv_for_card else {'Overall_Adv': overall}, idx, p['Week'])
            if metrics_img:
                image_paths.append(str(metrics_img))
            reasoning_img = _generate_reasoning_image(matchup, pick_side, bullets, idx, p['Week'])
            if reasoning_img:
                image_paths.append(str(reasoning_img))
        tweet_payloads.append({'text': tweet_text, 'image_path': image_paths[0] if image_paths else None, 'image_paths': image_paths})

    return tweet_payloads

def post_dick_picks_thread(week_label: Optional[str] = None, teaser_adjust: float = 6.0,
                           include_images: bool = True, dry_run: bool = False, blurb_char_limit: int = 200) -> List[str]:
    payloads = build_dick_picks_thread(week_label, teaser_adjust, include_images, blurb_char_limit)
    if not payloads:
        return []
    if dry_run:
        return [p['text'] for p in payloads]
    try:
        client = _get_client()
    except Exception as e:
        logging.error(f"Twitter client init failed: {e}")
        raise
    media_api = None
    try:
        if include_images and tweepy is not None:
            auth = tweepy.OAuth1UserHandler(os.getenv('TWITTER_API_KEY'), os.getenv('TWITTER_API_SECRET'),
                                            os.getenv('TWITTER_ACCESS_TOKEN'), os.getenv('TWITTER_ACCESS_SECRET'))
            media_api = tweepy.API(auth)  # type: ignore
    except Exception as e:  # pragma: no cover
        logging.warning(f"Media API init failed: {e}")
    posted_ids: List[str] = []
    reply_to: Optional[str] = None
    for p in payloads:
        media_ids = []
        paths = p.get('image_paths') or ([] if p.get('image_path') is None else [p['image_path']])
        if paths and media_api is not None:
            for imgp in paths[:4]:  # twitter allows up to 4
                try:
                    up = media_api.media_upload(filename=str(imgp))  # type: ignore
                    if hasattr(up, 'media_id'):
                        media_ids.append(up.media_id)
                except Exception as e:  # pragma: no cover
                    logging.error(f"Image upload failed: {e}")
        try:
            if media_ids:
                resp = client.create_tweet(text=p['text'], in_reply_to_tweet_id=reply_to, media_ids=media_ids) if reply_to else client.create_tweet(text=p['text'], media_ids=media_ids)
            else:
                resp = client.create_tweet(text=p['text'], in_reply_to_tweet_id=reply_to) if reply_to else client.create_tweet(text=p['text'])
            tweet_id = str(resp.data.get('id')) if hasattr(resp, 'data') and resp.data else ''
            posted_ids.append(tweet_id)
            reply_to = tweet_id if tweet_id else reply_to
        except Exception as e:  # pragma: no cover
            logging.error(f"Failed to post dick picks tweet: {e}")
            break
    return posted_ids

def generate_dick_picks_preview(week_label: Optional[str] = None, teaser_adjust: float = 6.0,
                                 blurb_char_limit: int = 200, dest_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate Dick Picks thread payloads with images saved locally (no posting).
    If dest_dir provided, copies images into that directory (created if missing) and updates image_path.
    Returns list of payload dicts (text, image_path or None).
    """
    payloads = build_dick_picks_thread(week_label=week_label, teaser_adjust=teaser_adjust,
                                       include_images=True, blurb_char_limit=blurb_char_limit)
    if not payloads:
        return []
    if dest_dir:
        out_dir = Path(dest_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        new_payloads: List[Dict[str, Any]] = []
        for p in payloads:
            paths = p.get('image_paths') or []
            copied = []
            for img_path in paths:
                if img_path and Path(img_path).exists():
                    target = out_dir / Path(img_path).name
                    try:
                        shutil.copyfile(img_path, target)
                        copied.append(str(target))
                    except Exception:
                        copied.append(img_path)
            # maintain single image_path for backward compat
            new_payloads.append({**p, 'image_paths': copied, 'image_path': copied[0] if copied else None})
        payloads = new_payloads
    return payloads

def generate_reasoning_template(week_label: Optional[str] = None, overwrite: bool = False) -> Path:
    """Create a reasoning template text file for the specified (or auto-detected) week.

    Structure per pick section:
    ## Week X – Pick i: AWAY @ HOME
    - Baseline Model Edge: <auto-filled overall edge & threshold>
    - Unit-Level Differential: <auto-filled off/def edges>
    - Game Script Expectation: <TODO>
    - Line Evaluation: <auto-filled line & quick fair cushion>
    - Teaser Consideration: <auto-filled teaser movement & key numbers>
    - Risk / Failure Modes: <TODO>
    - Why This Still Rates as a Play: <TODO>
    - Confidence Indicator: <auto-filled confidence>

    Returns path to the file.
    """
    resolved_week, picks = _fetch_upcoming_for_week(week_label)
    if not picks:
        raise RuntimeError("No picks found to generate template.")
    path = _reasoning_file_for_week(resolved_week)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Template already exists: {path}")
    wk_num = extract_week_number(resolved_week) or ''
    lines_out: List[str] = []
    teaser_adjust = 6.0
    for idx, p in enumerate(picks, start=1):
        away = p['Away_Team']; home = p['Home_Team']; pick_side = p['Pick_Side']
        overall = p.get('Overall_Adv')
        base_line = p.get('Base_Line')
        off_adv = None; def_adv = None
        # fetch extended details for more metrics
        detail = _fetch_pick_detail(p['Week'], home, away)
        if detail:
            off_adv = detail.get('Offense_Adv')
            def_adv = detail.get('Defense_Adv')
            if overall is None:
                overall = detail.get('Overall_Adv')
            if base_line is None:
                base_line = detail.get('Home_Line_Close') if pick_side == home else detail.get('Away_Line_Close')
        teaser_line = base_line + teaser_adjust if isinstance(base_line,(int,float)) else None
        thresh = Settings.ADVANTAGE_THRESHOLDS.get('Overall_Adv', 2.0)
        fair_line = None
        if isinstance(base_line,(int,float)) and isinstance(overall,(int,float)):
            # heuristic: fair shift half of overall advantage towards pick side
            fair_line = (base_line if base_line <=0 else -base_line) - (overall/2.0 if base_line <=0 else -(overall/2.0))
        cushion = None
        if fair_line is not None and isinstance(base_line,(int,float)):
            cushion = fair_line - base_line
        # key number crossings for teaser when favorite
        crossed = []
        if isinstance(base_line,(int,float)) and base_line < 0 and isinstance(teaser_line,(int,float)):
            for k in KEY_NUMBERS:
                if base_line < k < teaser_line:
                    crossed.append(str(k))
        lines_out.append(f"## Week {wk_num} – Pick {idx}: {away} @ {home}")
        lines_out.append(f"- Baseline Model Edge: Overall edge {overall:+.1f} vs threshold {thresh:.1f} (refine narrative)" if isinstance(overall,(int,float)) else "- Baseline Model Edge: <ADD>")
        if isinstance(off_adv,(int,float)) or isinstance(def_adv,(int,float)):
            lines_out.append(f"- Unit-Level Differential: Off {off_adv:+.1f} / Def {def_adv:+.1f} (expand where primary edge arises)".replace('+nan','+0.0'))
        else:
            lines_out.append("- Unit-Level Differential: <ADD>")
        lines_out.append("- Game Script Expectation: <ADD description of expected flow / leverage>")
        if isinstance(base_line,(int,float)):
            le_line = f"Line {format_line(base_line)}"
            if fair_line is not None and cushion is not None:
                le_line += f" vs fair {format_line(round(fair_line,1))} (cushion {cushion:+.1f})"
            lines_out.append(f"- Line Evaluation: {le_line} – add market context / injury checks")
        else:
            lines_out.append("- Line Evaluation: Moneyline value (add reasoning)")
        if isinstance(base_line,(int,float)) and isinstance(teaser_line,(int,float)):
            lines_out.append(f"- Teaser Consideration: {format_line(base_line)} -> {format_line(teaser_line)} crosses {', '.join(crossed) if crossed else 'key zones'} (assess quality)")
        else:
            lines_out.append("- Teaser Consideration: N/A or low value")
        lines_out.append("- Risk / Failure Modes: <List 2-3 concrete failure pathways>")
        lines_out.append("- Why This Still Rates as a Play: <Summarize multi-factor resilience>")
        conf = p.get('Confidence')
        lines_out.append(f"- Pick Strength: {conf}" if conf else "- Pick Strength: <ADD>")
        lines_out.append("")
    content = "\n".join(lines_out).rstrip()+"\n"
    path.write_text(content, encoding='utf-8')
    return path

def generate_reasoning_images_for_week(week_label: str, dest_dir: Optional[str] = None) -> List[str]:
    """Generate reasoning images for each pick in the week's reasoning file using the branded template.
    Returns list of image file paths. If dest_dir provided, copies images there.
    Uses existing reasoning file sections; pick index is derived from order in file.
    """
    reasoning_map = load_reasoning_map(week_label)
    if not reasoning_map:
        raise RuntimeError(f"No reasoning file or sections found for week {week_label}.")
    image_paths: List[str] = []
    # Preserve ordering by sorting header keys by natural pick number if present in file order
    # We re-read file to preserve order
    path = _reasoning_file_for_week(week_label)
    order_keys: List[str] = []
    try:
        content = path.read_text(encoding='utf-8')
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
        for sec in sections:
            sec = sec.strip()
            if not sec or not sec.lower().startswith('week'):
                continue
            header_line = sec.splitlines()[0]
            m = re.search(r':\s*([^\n]+)', header_line)
            matchup_raw = m.group(1).strip() if m else ''
            if matchup_raw:
                key = matchup_raw.replace(' ', '')
                order_keys.append(key)
    except Exception:
        order_keys = list(reasoning_map.keys())
    for idx, key in enumerate(order_keys, start=1):
        bullets = reasoning_map.get(key)
        if not bullets:
            continue
        matchup_disp = key.replace('@', ' @ ')
        # Pass empty pick_side (not used in reasoning image generation)
        img_path = _generate_reasoning_image(matchup_disp.replace(' ', ''), '', bullets, idx, week_label)
        if img_path:
            image_paths.append(str(img_path))
    if dest_dir and image_paths:
        out_dir = Path(dest_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        copied: List[str] = []
        for pth in image_paths:
            p = Path(pth)
            target = out_dir / p.name
            try:
                shutil.copyfile(p, target)
                copied.append(str(target))
            except Exception:
                copied.append(str(p))
        image_paths = copied
    return image_paths

