from datetime import date

from BSH.decide import Action, decide
from signals.analysis import analysis_score, detect_spike, fetch_price_history
from signals.combine import combine_scores
from signals.intuition import intuition_score
from signals.news import news_score
from tracker.degiro import fetch_positions
from tracker.portfolio import Position, portfolio_value


def evaluate_position(position: Position, day: date) -> Action:
    score = combine_scores(
        news=news_score(position.ticker, day),
        intuition=intuition_score(position.ticker),
        analysis=analysis_score(position.ticker, day),
    )
    spike = detect_spike(fetch_price_history(position.ticker, day, days=5))
    return decide(score, spike)


def main() -> None:
    today = date.today()
    positions = fetch_positions()
    print(f"Portfolio value: {portfolio_value(positions):.2f}")
    for position in positions:
        print(f"{position.ticker}: {evaluate_position(position, today)}")


if __name__ == "__main__":
    main()
