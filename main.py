from calculator import TriangleCalculator
from market_repo import MarketRepository

if __name__ == '__main__':
    market_repo = MarketRepository()
    tc = TriangleCalculator()
    market_repo.add_callback(tc.calculate)
    market_repo.run()
