from constants import (
    NEWS_DAYS,
    NEWS_FEEDS,
    NEWS_FILE,
    NEWS_HITS_FOR_FULL_SCORE,
    NEWS_USER_AGENT,
    SCORE_MAX,
)
from imports import (
    ElementTree,
    dataclass,
    date,
    html,
    json,
    parsedate_to_datetime,
    re,
    timedelta,
    urllib,
)
from signals.keywords import NEGATIVE, POSITIVE
from signals.scale import clamp_score


@dataclass(frozen=True)
class Headline:
    day: date
    title: str
    summary: str
    link: str


# ------------------------------------------------------- reading the feeds


def download(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": NEWS_USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def strip_html(text: str | None) -> str:
    """Remove tags and entities, collapse whitespace."""
    without_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def parse_pub_date(text: str | None) -> date:
    """Publication date of an RSS item, today if it is missing or unreadable."""
    try:
        return parsedate_to_datetime(text).date()
    except (TypeError, ValueError):
        return date.today()


def parse_item(item: ElementTree.Element) -> Headline:
    return Headline(
        day=parse_pub_date(item.findtext("pubDate")),
        title=strip_html(item.findtext("title")),
        summary=strip_html(item.findtext("description")),
        link=(item.findtext("link") or item.findtext("guid") or "").strip(),
    )


def parse_rss(xml_text: str) -> list[Headline]:
    """All items of an RSS 2.0 feed."""
    return [parse_item(item) for item in ElementTree.fromstring(xml_text).iter("item")]


def fetch_headlines() -> tuple[list[Headline], list[str]]:
    """Headlines from all feeds, plus an error message for every feed that failed."""
    headlines, errors = [], []
    for url in NEWS_FEEDS:
        try:
            headlines += parse_rss(download(url))
        except Exception as error:
            errors.append(f"{url}: {error}")
    return headlines, errors


# ------------------------------------------------------------- storage


def headline_key(headline: Headline) -> str:
    return headline.link or headline.title


def merge_headlines(stored: list[Headline], new: list[Headline]) -> list[Headline]:
    """Stored plus new headlines, without duplicates, oldest first."""
    merged = {headline_key(h): h for h in new}
    merged.update({headline_key(h): h for h in stored})
    return sorted(merged.values(), key=lambda h: h.day)


def load_headlines() -> list[Headline]:
    if not NEWS_FILE.exists():
        return []
    return [
        Headline(date.fromisoformat(h["day"]), h["title"], h["summary"], h["link"])
        for h in json.loads(NEWS_FILE.read_text())
    ]


def save_headlines(headlines: list[Headline]) -> None:
    raw = [
        {"day": h.day.isoformat(), "title": h.title, "summary": h.summary, "link": h.link}
        for h in headlines
    ]
    NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    NEWS_FILE.write_text(json.dumps(raw, indent=2, ensure_ascii=False))


def update_headlines() -> tuple[int, list[str]]:
    """Fetch the feeds and store what is new. Returns (new count, errors)."""
    fetched, errors = fetch_headlines()
    stored = load_headlines()
    merged = merge_headlines(stored, fetched)
    save_headlines(merged)
    return len(merged) - len(stored), errors


def headlines_since(headlines: list[Headline], day: date, days: int) -> list[Headline]:
    """Headlines of the last `days` days, up to and including `day`."""
    oldest = day - timedelta(days=days)
    return [h for h in headlines if oldest < h.day <= day]


# ------------------------------------------------- counting like cards


def count_hits(text: str, keywords: list[str]) -> int:
    """How often the keywords occur in the text. Duplicate keywords count once."""
    lowered = text.lower()
    return sum(lowered.count(keyword.lower()) for keyword in set(keywords))


def hit_counts(headlines: list[Headline]) -> tuple[int, int]:
    """(positive hits, negative hits) in the titles and summaries."""
    text = " | ".join(f"{h.title} {h.summary}" for h in headlines)
    return count_hits(text, POSITIVE), count_hits(text, NEGATIVE)


def balance_to_score(balance: int) -> float:
    """Count balance (positive hits minus negative hits) as a score of -5 to +5."""
    return round(clamp_score(balance / NEWS_HITS_FOR_FULL_SCORE * SCORE_MAX), 1)


def week_headlines(day: date) -> list[Headline]:
    return headlines_since(load_headlines(), day, NEWS_DAYS)


def news_score(day: date) -> float:
    positive, negative = hit_counts(week_headlines(day))
    return balance_to_score(positive - negative)