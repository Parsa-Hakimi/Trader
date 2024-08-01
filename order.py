from dataclasses import dataclass
from typing import Tuple, Literal, Optional


@dataclass
class Order:
    market: Tuple[str, str]
    side: Literal["buy", "sell"]
    amount: float
    price: float
    mode: str = 'limit'
    identifier: Optional[str] = None
    price_stop: Optional[float] = None
    price_limit_oco: Optional[float] = None

    def paid(self):
        if self.side == 'buy':
            return self.quote_token, self.amount * self.price
        else:
            return self.base_token, self.amount

    @property
    def base_token(self):
        return self.market[0]

    @property
    def quote_token(self):
        return self.market[1]
