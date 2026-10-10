"""Save the market sentiment of a day: python add_sentiment.py 7"""

from imports import argparse, date
from signals.intuition import IntuitionEntry, add_entry, intuition_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save market sentiment, 0 to 10.")
    parser.add_argument("score", type=float, help="0 = very bad market, 10 = green market")
    parser.add_argument("--text", default="", help="optional note")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    day = date.fromisoformat(args.date) if args.date else date.today()
    add_entry(IntuitionEntry(day, args.score, args.text))
    print(f"Saved {args.score} for {day}. Signal: {intuition_score(day):+.2f}")


if __name__ == "__main__":
    main()