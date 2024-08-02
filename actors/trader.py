import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

from lyrid import Actor, use_switch, switch, Message, Address
import sqlite3

import metrics
from bitpin_proxy import bitpin_proxy
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
        self._db = None
        self.update_orders_and_wallet(initial=True)

    @property
    def db(self):
        if self._db:
            return self._db

        self._db = sqlite3.connect('orders.db').cursor()
        self._db.execute("CREATE TABLE IF NOT EXISTS orders ("
                        "identifier TEXT PRIMARY KEY,"
                        "market0 TEXT,"
                        "market1 TEXT,"
                        "market_code TEXT,"
                        "side TEXT,"
                        "amount REAL,"
                        "price REAL,"
                        "created_at TEXT,"
                        "order_set_id TEXT"
                        ");")
        self._db.execute("CREATE TABLE IF NOT EXISTS done_orders ("
                        "identifier TEXT PRIMARY KEY,"
                        "market0 TEXT,"
                        "market1 TEXT,"
                        "market_code TEXT,"
                        "side TEXT,"
                        "amount1 REAL,"
                        "amount2 REAL,"
                        "price REAL,"
                        "expected_gain REAL,"
                        "expected_resource REAL,"
                        "average_price REAL,"
                        "gain REAL,"
                        "resource REAL,"
                        "exchanged1 REAL,"
                        "exchanged2 REAL,"
                        "created_at TEXT,"
                        "closed_at TEXT);")
        return self._db

    @switch.message(type=UpdateOrdersAndWallet)
    def handle_update_orders_and_wallet(self, sender: Address, message: UpdateOrdersAndWallet):
        self.update_orders_and_wallet()
        self.tell(sender, message=WalletData(open_orders=self.open_orders.copy(), wallet=self.wallet.copy()))

    @switch.message(type=PlaceOrderSet)
    def handle_place_order_set(self, sender: Address, message: PlaceOrderSet):
        self.place_order_set(message.order_set)
        self.tell(sender, message=WalletData(open_orders=self.open_orders.copy(), wallet=self.wallet.copy()))

    def check_old_open_order(self, order: Order):
        resp = bitpin_proxy.get_my_orders(active=False, identifier=order.identifier)
        if resp and resp["state"] == "closed":
            params = (
                order.identifier,
                order.market[0],
                order.market[1],
                order.extra['market']['code'],
                order.side,
                float(order.extra["amount1"]),
                float(order.extra["amount2"]),
                float(order.extra["price"]),
                float(order.extra["expected_gain"]),
                float(order.extra["expected_resource"]),
                float(order.extra["average_price"]),
                float(order.extra["gain"]),
                float(order.extra["resource"]),
                float(order.extra["exchanged1"]),
                float(order.extra["exchanged2"]),
                order.extra["created_at"],
                order.extra["closed_at"],
            )
            self.db.execute(f"INSERT INTO done_orders VALUES(" + ",".join(["?"] * len(params)) + ")", params)

    def update_orders_and_wallet(self, initial=False):
        if not initial:
            for order in self.open_orders:
                self.check_old_open_order(order)

        self.open_orders = bitpin_proxy.get_my_orders()
        self.wallet.clear()
        self.wallet.update(bitpin_proxy.get_wallet_info())

        logger.info("Open orders: %s", str(self.open_orders))
        logger.info("Wallet: %s", str(self.wallet))

    def place_order_set(self, order_set: List[Order]):
        logger.info('Placing orders: %s', str(order_set))

        order_set_id = uuid.uuid4()

        orders_placed = False
        with metrics.order_placement_duration.time():
            if self.verify_order_set(order_set):
                for order in order_set:
                    self._place_order(order, order_set_id=str(order_set_id))
                orders_placed = True

        if orders_placed:
            self.update_orders_and_wallet()

    def _place_order(self, order: Order, order_set_id: str):
        logger.info('Placing order: %s', str(order))
        order.identifier = str(uuid.uuid4())

        bitpin_proxy.place_order(
            market_id=MARKET_MAPPING.get(order.market),
            base_amount=order.amount,
            price=order.price,
            side=order.side,
            identifier=order.identifier,
            mode='market',  # Testing market mode to prevent open orders
        )
        # TODO: Check order is placed

        self.open_orders.append(order)
        params = (
            order.identifier, order.market[0], order.market[1], f"{order.market[0]}_{order.market[1]}", order.side,
            order.amount, order.price, datetime.now().isoformat(), order_set_id)
        self.db.execute(f"INSERT INTO orders VALUES(" + ",".join(["?"] * len(params)) + ")", params)

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
