import csv
import logging
import uuid
from dataclasses import dataclass
from typing import List, Literal, Tuple, Optional

from bitpin_proxy import bitpin_proxy
from market_repo import MarketRepository, get_market_base_and_quote, MARKET_MAPPING

logger = logging.getLogger(__name__)


class Triangle:
    def __init__(self, main_token, secondary_token, base_token):
        self.main_token = main_token
        self.secondary_token = secondary_token
        self.base_token = base_token

    @property
    def tokens(self) -> List[str]:
        return [self.main_token, self.secondary_token, self.base_token]

    def get_profit_market(self, market_repo: MarketRepository):
        p1 = market_repo.get_price(self.main_token, self.secondary_token)
        p2 = market_repo.get_price(self.secondary_token, self.base_token)
        p3 = market_repo.get_price(self.base_token, self.main_token)

        # print(f"LOOP1 {p1 * p2 - 1. / p3} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")
        # print(f"LOOP2 {p2 * p3 - 1. / p1} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")
        # print(f"LOOP3 {p1 * p3 - 1. / p2} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")

        print(f"=============={self.base_token}==============")
        print(p1 * p2 * p3)
        profit = abs((p1 * p2) * p3 - 1)
        if profit > 1e-6:
            print(
                f"PROFIT! {profit * 1e6} {self.main_token}->{self.secondary_token}={p1} {self.secondary_token}->{self.base_token}={p2} {self.base_token}->{self.main_token}={p3}")
        else:
            print(
                f"NONPROFIT! {profit * 1e6} {self.main_token}->{self.secondary_token}={p1} {self.secondary_token}->{self.base_token}={p2} {self.base_token}->{self.main_token}={p3}")

    def get_profit_ask_bid(self, market_repo: MarketRepository):
        a1 = market_repo.get_market_ask(self.base_token, self.main_token)
        a2 = market_repo.get_market_ask(self.base_token, self.secondary_token)
        a3 = market_repo.get_market_ask(self.secondary_token, self.main_token)
        b1 = market_repo.get_market_bid(self.base_token, self.main_token)
        b2 = market_repo.get_market_bid(self.base_token, self.secondary_token)
        b3 = market_repo.get_market_bid(self.secondary_token, self.main_token)

        if float(b1.get('price')) - float(a2.get('price')) * float(a3.get('price')) > 0:
            profit_per_unit = float(b1.get('price')) - float(a2.get('price')) * float(a3.get('price'))
            amount = min(float(b1.get('remain')), float(a2.get('remain')))
            profit = profit_per_unit * amount

            return {"base": self.base_token,
                    "main_market_optimal_position": "sell",
                    "main_market_order_amount": amount,
                    "main_market_price": float(b1.get('price')),
                    "secondary_market_optimal_position": "buy",
                    "secondary_market_order_amount": amount,
                    "secondary_market_price": float(a2.get('price')),
                    "secondary_quote_optimal_position": "buy",
                    "secondary_quote_order_amount": amount / float(a2.get('price')),
                    "secondary_quote_price": float(a3.get('price')),
                    "expected_profit": profit}

        elif -float(a1.get('price')) + float(b2.get('price')) * float(b3.get('price')) > 0:
            profit_per_unit = -float(a1.get('price')) + float(b2.get('price')) * float(b3.get('price'))
            amount = min(float(a1.get('remain')), float(b2.get('remain')))
            profit = profit_per_unit * amount

            return {"base": self.base_token,
                    "main_market_optimal_position": "buy",
                    "main_market_order_amount": amount,
                    "main_market_price": float(a1.get('price')),
                    "secondary_market_optimal_position": "sell",
                    "secondary_market_order_amount": amount,
                    "secondary_market_price": float(b2.get('price')),
                    "secondary_quote_optimal_position": "sell",
                    "secondary_quote_order_amount": amount / float(a2.get('price')),
                    "secondary_quote_price": float(b3.get('price')),
                    "expected_profit": profit}


@dataclass
class Order:
    market: Tuple[str, str]
    side: Literal["buy", "sell"]
    amount: float
    price: float
    identifier: Optional[str] = None

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


def _get_order_set_base_tokens(order_set):
    order_set_tokens = set()
    for order in order_set:
        order_set_tokens.add(order.base_token)
        order_set_tokens.add(order.quote_token)
    order_set_tokens.discard('USDT')
    order_set_tokens.discard('IRT')
    return order_set_tokens


class TraderAgent:
    def __init__(self):
        self.open_orders = []
        self.wallet = {}

        self.update_orders_and_wallet()

    def update_orders_and_wallet(self):
        self.open_orders = bitpin_proxy.get_my_open_orders()
        self.wallet = bitpin_proxy.get_wallet_info()

        logger.info("Open orders: %s", str(self.open_orders))
        logger.info("Wallet: %s", str(self.wallet))

    def place_order_set(self, order_set: List[Order]):
        logger.info('Placing orders: %s', str(order_set))
        if self.verify_order_set(order_set):
            for order in order_set:
                self._place_order(order)

    def _place_order(self, order: Order):
        logger.info('Placing order: %s', str(order))
        order.identifier = str(uuid.uuid4())

        # bitpin_proxy.place_order(
        #     market_id=MARKET_MAPPING.get(order.market),
        #     base_amount=order.amount,
        #     price=order.price,
        #     side=order.side,
        #     identifier=order.identifier,
        # )
        # TODO: Check order is placed

        self.open_orders.append(order)

    def verify_order_set(self, order_set: List[Order]) -> bool:
        logger.info('Verifying orders: %s', str(order_set))
        self.update_orders_and_wallet()

        order_set_tokens = _get_order_set_base_tokens(order_set)

        for oo in self.open_orders:
            if oo.market[0] in order_set_tokens or oo.market[1] in order_set_tokens:
                logger.info('There is already an open order for the base token :(')
                return False  # There is already an open order for the base token

        for order in order_set:
            token, amount = order.paid()
            if self.get_tradable_balance(token) < amount:
                logger.info(
                    'There is not enough tradable balance for %s (balance=%f,amount=%f) :(',
                    token,
                    self.get_tradable_balance(token),
                    amount,
                )
                return False

        logger.info('Orders verified')

        return True

    def get_tradable_balance(self, token: str) -> float:
        return self.wallet[token] - sum(o.paid()[1] for o in self.open_orders if o.paid()[0] == token)


trader_agent = TraderAgent()


class TriangleCalculator:
    def __init__(self):
        self.log_file = open('log_file.csv', mode='a')
        self.triangles = [
            Triangle('IRT', 'USDT', 'NOT'),
            Triangle('IRT', 'USDT', 'DOGE'),
            Triangle('IRT', 'USDT', 'TON'),
            Triangle('IRT', 'USDT', 'BTC'),
            Triangle('IRT', 'USDT', 'ETH'),
        ]

    def calculate(self, market_repo: MarketRepository, **kwargs):
        logger.info("Calculating triangles")
        writer = csv.writer(self.log_file)
        for triangle in self.triangles:
            logger.info("Checking triangle (%s)", " -> ".join(triangle.tokens))
            market_id = kwargs.get('market_id')
            if market_id:
                market_sides = get_market_base_and_quote(market_id)
                logger.info(market_sides)
                if market_sides[0] is not None:
                    if market_sides[0] not in triangle.tokens or market_sides[1] not in triangle.tokens:
                        logger.info("Sides not in market update, skipping.")
                        continue
            res = triangle.get_profit_ask_bid(market_repo)

            if res is not None:
                logger.info("Profitable trade: %s", str(res))

                o1 = Order(
                    market=(triangle.base_token, triangle.main_token),
                    side=res['main_market_optimal_position'],
                    amount=res['main_market_order_amount'],
                    price=res['main_market_price'],
                )

                o2 = Order(
                    market=(triangle.base_token, triangle.secondary_token),
                    side=res['secondary_market_optimal_position'],
                    amount=res['secondary_market_order_amount'],
                    price=res['secondary_market_price'],
                )

                o3 = Order(
                    market=(triangle.secondary_token, triangle.main_token),
                    side=res['secondary_quote_optimal_position'],
                    amount=res['secondary_quote_order_amount'],
                    price=res['secondary_quote_price'],
                )

                order_set = [o1, o2, o3]
                trader_agent.place_order_set(order_set)

                writer.writerow(res.values())

        self.log_file.flush()
