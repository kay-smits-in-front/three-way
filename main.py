from datetime import date

from BSH import Action, decide
from signals import analysis_score, detect_spike, fetch_price_history
from signals import combine_scores
from signals import intuition_score
from signals import news_score
from tracker import fetch_positions
from tracker import Position, portfolio_value


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
