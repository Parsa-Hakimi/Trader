import logging
import time

from lyrid import ActorSystem, Message
from prometheus_client import CollectorRegistry, multiprocess
from prometheus_client.twisted import MetricsResource
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site

from actors.market_handler import MarketHandler
from actors.position_finder import PositionFinder
from actors.trader import TraderAgent
from messages import Start

logger = logging.getLogger(__name__)


def run():
    system = ActorSystem(n_nodes=4)
    trader_agent = system.spawn(actor=TraderAgent())
    position_finder = system.spawn(actor=PositionFinder(trader_agent=trader_agent))
    market_actor = system.spawn(actor=MarketHandler(position_finder=position_finder, trader_agent=trader_agent), key='market')
    time.sleep(5)

    system.tell(market_actor, Start())

    # system.force_stop()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    root = Resource()
    root.putChild(b'metrics', MetricsResource(registry))

    factory = Site(root)
    reactor.listenTCP(8000, factory)
    reactor.run()
