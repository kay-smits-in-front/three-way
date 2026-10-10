from imports import date

from BSH.decide import Action, decide
from tracker.analysis import analysis_score, detect_spike
from signals.combine import combine_scores
from signals.intuition import describe_sentiment, intuition_score
from signals.news import news_score
from tracker.history import fetch_price_history
from tracker.portfolio import Position
from tracker.report import print_report


def evaluate_position(position: Position, day: date) -> Action:
    score = combine_scores(
        news=news_score(position.ticker, day),
        intuition=intuition_score(day),
        analysis=analysis_score(position.ticker, day),
    )
    spike = detect_spike(fetch_price_history(position.ticker, day, days=5))
    return decide(score, spike)


def main() -> None:
    print(describe_sentiment(date.today()))
    print()
    print_report()


if __name__ == "__main__":
    main()