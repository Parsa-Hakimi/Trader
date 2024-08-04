import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

from lyrid import Actor, use_switch, switch, Message, Address

import metrics
from bitpin_proxy import bitpin_proxy
from db import Order as DBOrder, OrderSet, OrderResult, db
from order import Order
from utils import MARKET_MAPPING

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)


def _get_order_set_base_tokens(order_set):
    order_set_tokens = set()
    for order in order_set:
        order_set_tokens.add(order.base_token)
        order_set_tokens.add(order.quote_token)
    order_set_tokens.discard('USDT')
    order_set_tokens.discard('IRT')
    return order_set_tokens


class UpdateOrdersAndWallet(Message):
    pass


@dataclass
class PlaceOrderSet(Message):
    order_set: List[Order]


@dataclass
class WalletData(Message):
    open_orders: List
    wallet: Dict

    def get_tradable_balance(self, token: str) -> float:
        return self.wallet[token] - sum(o.paid()[1] for o in self.open_orders if o.paid()[0] == token)


@use_switch
class TraderAgent(Actor):
    def __init__(self):
        self.open_orders = []
        self.wallet = defaultdict(float)
        self.update_orders_and_wallet(initial=True)

    @switch.message(type=UpdateOrdersAndWallet)
    def handle_update_orders_and_wallet(self, sender: Address, message: UpdateOrdersAndWallet):
        logger.info("Handling UpdateOrdersAndWallet message")
        with db:
            self.update_orders_and_wallet()
        self.tell(sender, message=WalletData(open_orders=self.open_orders.copy(), wallet=self.wallet.copy()))

    @switch.message(type=PlaceOrderSet)
    def handle_place_order_set(self, sender: Address, message: PlaceOrderSet):
        logger.info("Handling PlaceOrderSet message")
        with db:
            self.place_order_set(message.order_set)
        self.tell(sender, message=WalletData(open_orders=self.open_orders.copy(), wallet=self.wallet.copy()))

    def check_old_open_order(self, order: Order):
        resp = bitpin_proxy.get_my_orders(active=False, identifier=order.identifier)
        if resp and resp[0].extra["state"] == "closed":
            db_order = DBOrder.get(DBOrder.identifier == order.identifier)
            order_result = OrderResult(
                order=db_order,
                amount1=float(resp[0].extra.get("amount1") or -1),
                amount2=float(resp[0].extra.get('amount2') or -1),
                expected_gain=float(resp[0].extra.get('expected_gain') or -1),
                expected_resource=float(resp[0].extra.get('expected_resource') or -1),
                average_price=float(resp[0].extra.get('average_price') or -1),
                gain=float(resp[0].extra.get('gain') or -1),
                resource=float(resp[0].extra.get('resource') or -1),
                exchanged1=float(resp[0].extra.get('exchanged1') or -1),
                exchanged2=float(resp[0].extra.get('exchanged2') or -1),
                real_created_at=datetime.fromisoformat(resp[0].extra.get("created_at").replace('Z', '')),
                closed_at=datetime.fromisoformat(resp[0].extra.get("created_at").replace('Z', '')),
            )
            order_result.save()

    def update_orders_and_wallet(self, initial=False):
        try:
            if not initial:
                for order in self.open_orders:
                    self.check_old_open_order(order)
        except Exception as error:
            import traceback
            traceback.print_exception(error)

        self.open_orders = bitpin_proxy.get_my_orders()
        self.wallet.clear()
        self.wallet.update(bitpin_proxy.get_wallet_info())

        logger.info("Open orders: %s", str(self.open_orders))
        logger.info("Wallet: %s", str(self.wallet))

    def place_order_set(self, order_set: List[Order]):
        logger.info('Placing orders: %s', str(order_set))

        orders_placed = False
        with metrics.order_placement_duration.time():
            if self.verify_order_set(order_set):
                db_order_set = OrderSet(base_tokens=_get_order_set_base_tokens(order_set))
                db_order_set.save()

                for order in order_set:
                    self._place_order(order, order_set=db_order_set)
                orders_placed = True

        if orders_placed:
            time.sleep(1)  # :|
            self.update_orders_and_wallet()

    def _place_order(self, order: Order, order_set: OrderSet):
        logger.info('Placing order: %s', str(order))
        order.identifier = str(uuid.uuid4())

        self.run_in_background(
            bitpin_proxy.place_order, args=(
                MARKET_MAPPING.get(order.market),
                order.amount,
                order.price,
                order.side,
                'market',  # Testing market mode to prevent open orders
                order.identifier,
            ))
        # TODO: Check order is placed

        self.open_orders.append(order)
        self.check_db_initialized()
        db_order = DBOrder(
            identifier=order.identifier,
            market_0=order.market[0],
            market_1=order.market[1],
            market_code=f"{order.market[0]}_{order.market[1]}",
            side=order.side,
            amount=order.amount,
            price=order.price,
            created_at=datetime.now().isoformat(),
            order_set=order_set,
        )
        db_order.save()

    def verify_order_set(self, order_set: List[Order]) -> bool:
        logger.info('Verifying orders: %s', str(order_set))

        order_set_tokens = _get_order_set_base_tokens(order_set)

        for oo in self.open_orders:
            if oo.market[0] in order_set_tokens or oo.market[1] in order_set_tokens:
                logger.info('There is already an open order for the base token :(')
                return False  # Skip for now...

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
