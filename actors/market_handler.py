from dataclasses import dataclass

from lyrid import use_switch, Actor, Address, switch

from actor_system import logger
from messages import Start, MarketUpdate
from market_repo import MarketRepository


@use_switch
@dataclass
class MarketHandler(Actor):
    position_finder: Address
    trader_agent: Address

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
        self.tell(self.position_finder, MarketUpdate(self.market_repo.only_data(), market_id=market_id))
