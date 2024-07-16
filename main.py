from calculator import TriangleCalculator
from market_repo import MarketRepository

if __name__ == '__main__':
    market_repo = MarketRepository()
    tc = TriangleCalculator()
    market_repo.add_callback(MarketRepository.update_by_order_list)
    market_repo.add_callback(tc.calculate)
    while True:
        try:
            market_repo.run()
        except:
            pass
