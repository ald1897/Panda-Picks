"""Generate Dick Picks tweet thread preview (with images) for a given week.
Usage:
  python scripts/generate_week_thread_preview.py --week WEEK2 --out data/picks/week2_tweet_preview
Writes payloads.json and prints summary with image file paths.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

try:
    from panda_picks.publish.twitter import generate_dick_picks_preview
except ImportError:
    # Add project root to path then retry
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT = SCRIPT_DIR.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from panda_picks.publish.twitter import generate_dick_picks_preview  # type: ignore

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--week', default='WEEK2', help='Week label, e.g. WEEK2')
    ap.add_argument('--out', default='data/picks/week2_tweet_preview', help='Destination directory for images & JSON')
    ap.add_argument('--teaser', type=float, default=6.0, help='Teaser adjustment points')
    ap.add_argument('--char-limit', type=int, default=180, help='Primary blurb char limit per pick tweet')
    args = ap.parse_args()
    out_dir = Path(args.out)
    payloads = generate_dick_picks_preview(week_label=args.week, teaser_adjust=args.teaser,
                                           blurb_char_limit=args.char_limit, dest_dir=str(out_dir))
    if not payloads:
        print(f"No payloads generated for {args.week}. Ensure picks exist.")
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / 'payloads.json'
    json_path.write_text(json.dumps(payloads, indent=2), encoding='utf-8')
    print(f"Generated {len(payloads)} tweet payloads -> {json_path}")
    for idx, p in enumerate(payloads, start=1):
        imgs = p.get('image_paths') or []
        first_line = p['text'].splitlines()[0] if p['text'] else ''
        print(f"Tweet {idx}: {len(imgs)} images | First line: {first_line[:120]}")
        for ip in imgs:
            print('  IMG:', ip)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
