"""Save your market intuition without running main: python sentiment.py 3"""

from imports import argparse, date
from signals.intuition import IntuitionEntry, add_entry, intuition_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save market intuition, -5 to +5.")
    parser.add_argument("score", type=float, help="-5 = very bad market, +5 = green market")
    parser.add_argument("--text", default="", help="optional note")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    day = date.fromisoformat(args.date) if args.date else date.today()
    add_entry(IntuitionEntry(day, args.score, args.text))
    print(f"Saved {args.score:+g} for {day}. Intuition now: {intuition_score(day):+g}")


if __name__ == "__main__":
    main()