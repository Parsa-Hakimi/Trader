from market_repo import MarketRepository


class Triangle:
    def __init__(self, main_token, token1, token2):
        self.main_token = main_token
        self.token1 = token1
        self.token2 = token2

    def get_profit(self, market_repo: MarketRepository):
        p1 = market_repo.get_price(self.main_token, self.token1)
        p2 = market_repo.get_price(self.token1, self.token2)
        p3 = market_repo.get_price(self.token2, self.main_token)

        # print(f"LOOP1 {p1 * p2 - 1. / p3} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")
        # print(f"LOOP2 {p2 * p3 - 1. / p1} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")
        # print(f"LOOP3 {p1 * p3 - 1. / p2} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")

        print(f"=============={self.token2}==============")
        print(p1 * p2 * p3)
        profit = abs((p1 * p2) * p3 - 1)
        if profit > 1e-6:
            print(
                f"PROFIT! {profit * 1e6} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")
        else:
            print(
                f"NONPROFIT! {profit * 1e6} {self.main_token}->{self.token1}={p1} {self.token1}->{self.token2}={p2} {self.token2}->{self.main_token}={p3}")


class TriangleCalculator:
    def __init__(self):
        self.triangles = [
            Triangle('IRT', 'USDT', 'NOT'),
            Triangle('IRT', 'USDT', 'METIS'),
        ]

    def calculate(self, market_repo: MarketRepository):
        print("CALCING")
        for triangle in self.triangles:
            triangle.get_profit(market_repo)
