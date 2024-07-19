from typing import Tuple


def get_market_base_and_quote(market_id: int) -> Tuple[str, str] | Tuple[None, None]:
    try:
        market = next(filter(lambda m: m[1] == market_id, MARKET_MAPPING.items()))
        return market[0]
    except StopIteration:
        return None, None


MARKET_MAPPING = {
    ('USDT', 'IRT'): 5,
    ('NOT', 'IRT'): 772,
    ('NOT', 'USDT'): 773,
    # ('METIS', 'IRT'): 365,
    # ('METIS', 'USDT'): 366,
    # ('BTC', 'IRT'): 1,
    # ('BTC', 'USDT'): 2,
    # ('ETH', 'USDT'): 3,
    # ('ETH', 'IRT'): 4,
    # ('TON', 'IRT'): 355,
    # ('TON', 'USDT'): 356,
    # ('DOGE', 'IRT'): 62,
    # ('DOGE', 'USDT'): 63,
}
