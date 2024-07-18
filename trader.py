import logging
import uuid
from typing import List

from bitpin_proxy import bitpin_proxy
from order import Order

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
