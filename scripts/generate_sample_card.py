"""Generate a sample styled metrics image (white panel card) for manual preview.

Usage (from project root):
  python scripts/generate_sample_card.py \
      --matchup BLT@BUF --pick BLT --base-line 0 --teaser 6 --overall -11.3 \
      --offense 4.0 --defense -27.3 --confidence 72% --week "Week 1"

All arguments have defaults matching the design screenshot, so you can simply run:
  python scripts/generate_sample_card.py

The script prints the output path. On Windows it will attempt to open the image automatically unless --no-open is set.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Import the internal generator
try:
    from panda_picks.publish.twitter import _generate_styled_metrics_image  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"Import failed: {e}")
    sys.exit(1)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a styled metrics card image")
    p.add_argument('--matchup', default='BLT@BUF', help='Matchup in AWAY@HOME form')
    p.add_argument('--pick', dest='pick_side', default='BLT', help='Picked side (team code)')
    p.add_argument('--base-line', type=float, default=0.0, help='Base spread line relative to pick side (0 for PK)')
    p.add_argument('--teaser', type=float, default=6.0, help='Teaser adjustment to add to base line')
    p.add_argument('--overall', type=float, default=-11.3, help='Overall advantage value (±20 scaled range expected)')
    p.add_argument('--offense', type=float, default=4.0, help='Offense advantage value')
    p.add_argument('--defense', type=float, default=-27.3, help='Defense advantage value')
    p.add_argument('--confidence', default='72%', help='Confidence percentage (e.g. 72%) or 0-100 number')
    p.add_argument('--week', default='Week 1', help='Week label (e.g., "Week 1")')
    p.add_argument('--out-dir', default=None, help='Optional directory to copy the generated image into')
    p.add_argument('--no-open', action='store_true', help='Do not auto-open the generated image')
    return p.parse_args()

def main():
    args = parse_args()
    teaser_line = args.base_line + args.teaser
    lines = {'base_line': args.base_line, 'teaser_line': teaser_line}
    adv = {
        'Overall_Adv': args.overall,
        'Offense_Adv': args.offense,
        'Defense_Adv': args.defense,
        'Confidence': args.confidence,
    }

    img_path = _generate_styled_metrics_image(args.matchup, args.pick_side, lines, adv, pick_index=1, week_label=args.week)
    if not img_path:
        print('Failed to generate image (returned None).')
        sys.exit(2)

    final_path = Path(img_path)
    if args.out_dir:
        od = Path(args.out_dir)
        od.mkdir(parents=True, exist_ok=True)
        target = od / final_path.name
        try:
            target.write_bytes(final_path.read_bytes())
            final_path = target
        except Exception as e:  # pragma: no cover
            print(f'Copy to out-dir failed: {e}')
    print(f'Generated image: {final_path}')
    if not args.no_open and sys.platform.startswith('win'):
        try:
            import os
            os.startfile(str(final_path))  # type: ignore[attr-defined]
        except Exception:
            pass

if __name__ == '__main__':  # pragma: no cover
    main()
