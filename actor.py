import logging
import time
from dataclasses import dataclass

from lyrid import ActorSystem, Actor, Address, Message, switch, use_switch
from prometheus_client import CollectorRegistry, multiprocess
from prometheus_client.twisted import MetricsResource
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site

from market_repo import MarketRepository
from trader import trader_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SetStack:
    def __init__(self):
        self.set = set()
        self.stack = []

    def add(self, value):
        if value not in self.set:
            self.set.add(value)
            self.stack.append(value)
        else:
            self.stack.remove(value)
            self.stack.append(value)

    def pop(self):
        if len(self.stack) > 0:
            value = self.stack.pop()
            self.set.remove(value)
            return value

    def __len__(self):
        return len(self.stack)


@dataclass
class Start(Message):
    pass


@use_switch
@dataclass
class MarketActor(Actor):
    trader: Address

    @switch.message(type=Start)
    def handle_start(self, sender: Address, message: Start):
        logger.info("MarketActor: Handling Start")
        self.market_repo = MarketRepository(True)
        self.market_repo.add_callback(self.market_updated)
        while True:
            try:
                self.market_repo.run()
            except KeyboardInterrupt:
                break
            except:
                pass

    def market_updated(self, market_repo, market_id):
        logger.info("MARKET UPDATED: %s", str(market_id))
        self.tell(self.trader, MarketUpdate(self.market_repo.only_data(), market_id=market_id))


@dataclass
class MarketUpdate(Message):
    market_repo: MarketRepository
    market_id: int


class CalculationDone(Message):
    pass


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
        TriangleCalculator().calculate(self.latest_market_data, market_id=market_id)


if __name__ == "__main__":
    system = ActorSystem(n_nodes=4)
    trader = system.spawn(actor=PositionFinder())
    market_actor = system.spawn(actor=MarketActor(trader=trader), key='market')
    time.sleep(2)

    system.tell(market_actor, Start())

    # system.force_stop()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    root = Resource()
    root.putChild(b'metrics', MetricsResource(registry))

    factory = Site(root)
    reactor.listenTCP(8000, factory)
    reactor.run()
