from dataclasses import dataclass
from typing import Tuple, Literal, Optional, Dict


@dataclass
class Order:
    market: Tuple[str, str]
    side: Literal["buy", "sell"]
    amount: float
    price: float
    identifier: Optional[str] = None
    extra: Optional[Dict] = None

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
