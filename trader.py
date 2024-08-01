import logging
import uuid
from collections import defaultdict
from typing import List

import metrics
from bitpin_proxy import bitpin_proxy
from order import Order
from utils import MARKET_MAPPING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        self.wallet = defaultdict(float)

        self.update_orders_and_wallet()

    def update_orders_and_wallet(self):
        self.open_orders = bitpin_proxy.get_my_open_orders()
        self.wallet.clear()
        self.wallet.update(bitpin_proxy.get_wallet_info())

        logger.info("Open orders: %s", str(self.open_orders))
        logger.info("Wallet: %s", str(self.wallet))

    def place_order_set(self, order_set: List[Order]):
        logger.info('Placing orders: %s', str(order_set))

        orders_placed = False
        with metrics.order_placement_duration.time():
            if self.verify_order_set(order_set):
                for order in order_set:
                    self._place_order(order)
                orders_placed = True

        if orders_placed:
            self.update_orders_and_wallet()

    def _place_order(self, order: Order):
        logger.info('Placing order: %s', str(order))
        order.identifier = str(uuid.uuid4())

        kwargs = {}
        if order.mode == 'oco':
            kwargs['price_stop'] = order.price_stop
            kwargs['price_limit_oco'] = order.price_limit_oco

        bitpin_proxy.place_order(
            market_id=MARKET_MAPPING.get(order.market),
            base_amount=order.amount,
            price=order.price,
            side=order.side,
            identifier=order.identifier,
            **kwargs,
        )
        # TODO: Check order is placed

        self.open_orders.append(order)

    def verify_order_set(self, order_set: List[Order]) -> bool:
        logger.info('Verifying orders: %s', str(order_set))

        order_set_tokens = _get_order_set_base_tokens(order_set)

        for oo in self.open_orders:
            if oo.market[0] in order_set_tokens or oo.market[1] in order_set_tokens:
                logger.info('There is already an open order for the base token :(')
                # return False  # Skip for now...

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
