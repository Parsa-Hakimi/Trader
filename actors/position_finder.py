from lyrid import use_switch, Actor, switch, Address

import metrics
from actor_system import logger
from messages import MarketUpdate
from utils import SetStack
from actors.trader import trader_agent


@use_switch
class PositionFinder(Actor):
    def __init__(self):
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
        if self.market_update_count % 25 == 0:
            try:
                trader_agent.update_orders_and_wallet()
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
            TriangleCalculator().calculate(self.latest_market_data, market_id=market_id)
