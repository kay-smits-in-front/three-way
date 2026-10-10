from BSH.overview import DecisionRow, format_decision_table
from imports import date
from signals.analysis import analyse
from signals.intuition import ask_intuition
from tracker.holdings import load_holdings
from tracker.report import print_report


def ask_news_score() -> float:
    """Ask for a manually assessed news score between -5 and +5."""
    while True:
        answer = input(
            "Nieuwsinschatting afgelopen week, -5 tot +5 "
            "(bijv. -1,5; Enter = 0): "
        ).strip().replace(",", ".")

        if not answer:
            return 0.0

        try:
            score = float(answer)
            if -5 <= score <= 5:
                return score
        except ValueError:
            pass

        print("Typ een getal tussen -5 en +5, bijvoorbeeld -1,5 of 2.")


def analyse_all(day: date) -> list:
    """Financial analysis of every holding, one by one."""
    analyses = []
    for ticker in load_holdings():
        print(f"  analyse {ticker} ...")
        analyses.append(analyse(ticker, day))
    return analyses


def main() -> None:
    day = date.today()
    news = ask_news_score()
    print()
    intuition = ask_intuition(day)
    print("\\nFinanciele analyse per aandeel (Yahoo), dit duurt even:")
    analyses = analyse_all(day)
    rows = [DecisionRow(a, news, intuition) for a in analyses]
    print()
    print(format_decision_table(rows))
    print()
    print_report()


if __name__ == "__main__":
    main()
