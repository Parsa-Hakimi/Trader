import logging
from dataclasses import dataclass
from typing import List

from lyrid import use_switch, Actor, switch, Address, Message

import metrics
from messages import MarketUpdate
from order import Order
from utils import SetStack
from actors.trader import UpdateOrdersAndWallet, PlaceOrderSet, WalletData

logger = logging.getLogger(__name__)


@use_switch
@dataclass
class PositionFinder(Actor):
    trader_agent: Address

    def __init__(self, trader_agent: Address):
        self.trader_agent = trader_agent
        self._wallet_data = WalletData([], {})
        self.busy = False
        self.queued_markets = SetStack()  # Use stack to handle most updated markets first, maybe we need to change that
        self.latest_market_data = None
        self.market_update_count = 0

    @switch.message(type=MarketUpdate)
    def handle_market_update(self, sender: Address, message: MarketUpdate):
        logger.info("Handling market update")
        self.latest_market_data = message.market_repo
        if self.busy:
            logger.info("Busy! Put in queue")
            self.queued_markets.add(message.market_id)
        else:
            logger.info("Running calc in bg")
            self.busy = True
            self.run_in_background(self.calculate, args=(message.market_id,))

    @switch.background_task_exited(exception=None)
    def calc_done(self):
        logger.info("bg task done")
        self.try_running_queued_tasks()

    def try_running_queued_tasks(self):
        self.market_update_count += 1
        if self.market_update_count % 50 == 0:
            try:
                self.tell(self.trader_agent, UpdateOrdersAndWallet())
            except:
                pass

        if self.queued_markets:
            market_id = self.queued_markets.pop()
            logger.info("running another")
            self.run_in_background(self.calculate, args=(market_id,))
        else:
            self.busy = False

    @switch.background_task_exited(exception=Exception)
    def calc_done_exc(self, exception: Exception):
        logger.info("bg task done with exception %s", exception)
        self.try_running_queued_tasks()

    def calculate(self, market_id: int):
        from calculator import TriangleCalculator

        with metrics.calc_duration.time():
            TriangleCalculator(owner=self).calculate(self.latest_market_data, market_id=market_id)

    def place_order_set(self, order_set):
        self.tell(self.trader_agent, PlaceOrderSet(order_set))

    def wallet_data(self):
        return self._wallet_data
