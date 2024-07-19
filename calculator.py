import csv
import logging
from typing import List

from market_repo import MarketRepository
from order import Order
from trader import trader_agent
from utils import get_market_base_and_quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
fh = logging.FileHandler('trianglelog.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

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

        if b1 and a2 and a3 and float(b1.get('price')) - float(a2.get('price')) * float(a3.get('price')) > 0:
            profit_per_unit = float(b1.get('price')) - float(a2.get('price')) * float(a3.get('price'))
            amount = min(float(b1.get('remain')), float(a2.get('remain')))

            amount = min(amount, trader_agent.wallet[self.base_token])
            tether_amount = trader_agent.wallet[self.main_token] / float(a3.get('price'))
            tether_amount = min(tether_amount, trader_agent.wallet[self.secondary_token])
            amount = min(amount, tether_amount / float(a2.get('price')))

            profit = profit_per_unit * amount

            return {"base": self.base_token,
                    "main_market_optimal_position": "sell",
                    "main_market_order_amount": amount,
                    "main_market_price": float(b1.get('price')),
                    "secondary_market_optimal_position": "buy",
                    "secondary_market_order_amount": amount,
                    "secondary_market_price": float(a2.get('price')),
                    "secondary_quote_optimal_position": "buy",
                    "secondary_quote_order_amount": amount * float(a2.get('price')),
                    "secondary_quote_price": float(a3.get('price')),
                    "expected_profit": profit}

        elif a1 and b2 and b3 and -float(a1.get('price')) + float(b2.get('price')) * float(b3.get('price')) > 0:
            profit_per_unit = -float(a1.get('price')) + float(b2.get('price')) * float(b3.get('price'))
            amount = min(float(a1.get('remain')), float(b2.get('remain')))

            amount = min(amount, trader_agent.wallet[self.base_token])
            rial_amount = trader_agent.wallet[self.secondary_token] * float(b3.get('price'))
            rial_amount = min(rial_amount, trader_agent.wallet[self.main_token])
            amount = min(amount, rial_amount / float(a1.get('price')))

            profit = profit_per_unit * amount

            return {"base": self.base_token,
                    "main_market_optimal_position": "buy",
                    "main_market_order_amount": amount,
                    "main_market_price": float(a1.get('price')),
                    "secondary_market_optimal_position": "sell",
                    "secondary_market_order_amount": amount,
                    "secondary_market_price": float(b2.get('price')),
                    "secondary_quote_optimal_position": "sell",
                    "secondary_quote_order_amount": amount * float(b2.get('price')),
                    "secondary_quote_price": float(b3.get('price')),
                    "expected_profit": profit}


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
                if res['expected_profit'] > 100:
                    logger.info("Placing orders...")
                    trader_agent.place_order_set(order_set)

                writer.writerow(res.values())

        self.log_file.flush()
