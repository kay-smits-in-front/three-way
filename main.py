from BSH.overview import DecisionRow, format_decision_table
from imports import date
from signals.analysis import analyse
from signals.intuition import ask_intuition
from signals.news import (
    balance_to_score,
    hit_counts,
    update_headlines,
    week_headlines,
)
from tracker.holdings import load_holdings
from tracker.report import print_report


def refresh_news() -> None:
    """Fetch the feeds and tell what happened."""
    new, errors = update_headlines()
    print(f"Nieuws opgehaald: {new} nieuwe berichten.")
    for error in errors:
        print(f"  Feed mislukt: {error}")


def show_news(day: date) -> float:
    """Count the keyword hits of the last week like cards and show the balance."""
    articles = week_headlines(day)
    positive, negative = hit_counts(articles)
    balance = positive - negative
    score = balance_to_score(balance)
    print(
        f"NIEUWS, laatste 7 dagen ({len(articles)} berichten): "
        f"+{positive} positief, -{negative} negatief, balans {balance:+d} "
        f"-> score {score:+.1f}"
    )
    return score


def analyse_all(day: date) -> list:
    """Financial analysis of every holding, one by one."""
    analyses = []
    for ticker in load_holdings():
        print(f"  analyse {ticker} ...")
        analyses.append(analyse(ticker, day))
    return analyses


def main() -> None:
    day = date.today()
    refresh_news()
    news = show_news(day)
    print()
    intuition = ask_intuition(day)
    print("\nFinanciele analyse per aandeel (Yahoo), dit duurt even:")
    analyses = analyse_all(day)
    rows = [DecisionRow(a, news, intuition) for a in analyses]
    print()
    print(format_decision_table(rows))
    print()
    print_report()


if __name__ == "__main__":
    main()