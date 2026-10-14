"""Weekly update: python weekly.py"""

from imports import date
from signals.forecasts import collect_forecasts, format_table, save_weekly


def main() -> None:
    results = collect_forecasts()
    save_weekly(date.today(), results)
    print(format_table(results))


if __name__ == "__main__":
    main()