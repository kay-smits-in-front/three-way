"""The two scores that Kay types in at every check."""

from constants import SCORE_MAX


def parse_score(text: str, default: float) -> float:
    """Typed answer to a score. Empty gives the default, a comma works as a point."""
    cleaned = text.strip().replace(",", ".")
    if cleaned == "":
        return default
    score = float(cleaned)
    if not -SCORE_MAX <= score <= SCORE_MAX:
        raise ValueError(f"Score must be between -5 and +5, got {score:g}")
    return score


def read_answer(prompt: str) -> str:
    """One line from the terminal. No terminal input counts as an empty answer."""
    try:
        return input(prompt)
    except EOFError:
        return ""


def ask_score(question: str, default: float) -> float:
    """Ask until the answer is a score from -5 to +5. Enter keeps the default."""
    prompt = f"{question}, -5 tot +5 (Enter = {default:+g}): "
    while True:
        try:
            return parse_score(read_answer(prompt), default)
        except ValueError:
            print("Typ een getal tussen -5 en +5, bijvoorbeeld 3 of -2,5.")


def ask_scores(default_news: float, default_intuition: float) -> tuple[float, float]:
    news = ask_score("Nieuwsinschatting sinds de vorige check", default_news)
    intuition = ask_score("Jouw intuitie voor de markt", default_intuition)
    return news, intuition