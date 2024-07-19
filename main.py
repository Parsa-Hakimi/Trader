import logging

from lyrid import ActorSystem

from calculator import TriangleCalculator
from market_repo import MarketRepository

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    system = ActorSystem(n_nodes=2)
    market_repo = MarketRepository()
    def market_updated()
    tc = TriangleCalculator()
    # market_repo.add_callback(MarketRepository.update_by_order_list)
    market_repo.add_callback(tc.calculate)
    while True:
        try:
            market_repo.run()
        except KeyboardInterrupt:
            break
        except:
            pass
