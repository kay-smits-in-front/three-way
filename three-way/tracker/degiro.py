from constants import (
    ENV_DEGIRO_INT_ACCOUNT,
    ENV_DEGIRO_PASSWORD,
    ENV_DEGIRO_TOTP_SECRET,
    ENV_DEGIRO_USERNAME,
    POSITION_TYPE_PRODUCT,
)
from imports import API, Credentials, UpdateOption, UpdateRequest, os
from tracker.portfolio import Position


def build_credentials() -> Credentials:
    """Read DEGIRO credentials from environment variables."""
    int_account = os.environ.get(ENV_DEGIRO_INT_ACCOUNT)
    return Credentials(
        username=os.environ[ENV_DEGIRO_USERNAME],
        password=os.environ[ENV_DEGIRO_PASSWORD],
        int_account=int(int_account) if int_account else None,
        totp_secret_key=os.environ.get(ENV_DEGIRO_TOTP_SECRET),
    )


def connect(credentials: Credentials) -> API:
    api = API(credentials=credentials)
    api.connect()
    return api


def fetch_portfolio_rows(api: API) -> list[dict]:
    """Return the raw portfolio rows from DEGIRO."""
    update = api.get_update(
        request_list=[UpdateRequest(option=UpdateOption.PORTFOLIO, last_updated=0)],
        raw=True,
    )
    return update["portfolio"]["value"]


def row_to_dict(row: dict) -> dict:
    """Turn [{'name': 'size', 'value': 3}, ...] into {'size': 3, ...}."""
    return {item["name"]: item.get("value") for item in row["value"]}


def is_open_product(row: dict) -> bool:
    return row.get("positionType") == POSITION_TYPE_PRODUCT and row.get("size", 0) > 0


def fetch_symbols(api: API, product_ids: list[int]) -> dict[int, str]:
    """Map DEGIRO product ids to ticker symbols."""
    info = api.get_products_info(product_list=product_ids, raw=True)
    return {
        int(product_id): item.get("symbol") or item.get("name", str(product_id))
        for product_id, item in info["data"].items()
    }


def build_positions(rows: list[dict], symbols: dict[int, str]) -> list[Position]:
    return [
        Position(
            ticker=symbols[int(row["id"])],
            quantity=float(row["size"]),
            price=float(row["price"]),
        )
        for row in rows
    ]


def fetch_positions() -> list[Position]:
    api = connect(build_credentials())
    try:
        rows = [row_to_dict(r) for r in fetch_portfolio_rows(api)]
        open_rows = [r for r in rows if is_open_product(r)]
        symbols = fetch_symbols(api, [int(r["id"]) for r in open_rows])
        return build_positions(open_rows, symbols)
    finally:
        api.logout()
