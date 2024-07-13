from market_repo import MarketRepository
import csv


class Triangle:
    def __init__(self, main_token, token1, token2):
        self.main_token = main_token
        self.token1 = token1
        self.token2 = token2

    def get_profit_market(self, market_repo: MarketRepository):
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

    def get_profit_ask_bid(self, market_repo: MarketRepository):
        a1 = market_repo.get_market_ask(self.token2, self.main_token)
        a2 = market_repo.get_market_ask(self.token2, self.token1)
        a3 = market_repo.get_market_ask(self.token1, self.main_token)
        b1 = market_repo.get_market_bid(self.token2, self.main_token)
        b2 = market_repo.get_market_bid(self.token2, self.token1)
        b3 = market_repo.get_market_bid(self.token1, self.main_token)

        if float(b1.get('price')) - float(a2.get('price')) * float(a3.get('price')) > 0:
            profit_per_unit = float(b1.get('price')) - float(a2.get('price')) * float(a3.get('price'))
            amount = min(float(b1.get('remain')), float(a2.get('remain')))
            profit = profit_per_unit * amount

            return {"base":self.token2,
                    "main_market_optimal_position":"sell",
                   "main_market_order_amount": amount,
                    "main_market_price": float(b1.get('price')),
                  "secondary_market_optimal_position":"buy",
                  "secondary_market_order_amount": amount,
                    "secondary_market_price":float(a2.get('price')),
                  "secondary_quote_optimal_position":"buy",
                 "secondary_quote_order_amount": amount/float(a2.get('price')),
                 "secondary_quote_price": float(a3.get('price')),
                 "expected_profit": profit}

        elif -float(a1.get('price')) + float(b2.get('price')) * float(b3.get('price')) > 0:
            profit_per_unit = -float(a1.get('price')) + float(b2.get('price')) * float(b3.get('price'))
            amount = min(float(a1.get('remain')), float(b2.get('remain')))
            profit = profit_per_unit * amount

            return {"base":self.token2,
                    "main_market_optimal_position":"buy",
                    "main_market_order_amount": amount,
                    "main_market_price": float(a1.get('price')),
                 "secondary_market_optimal_position":"sell",
                  "secondary_market_order_amount": amount,
                  "secondary_market_price":float(b2.get('price')),
                  "secondary_quote_optimal_position":"sell",
                  "secondary_quote_order_amount": amount/float(a2.get('price')),
                 "secondary_quote_price": float(b3.get('price')),
                 "expected_profit": profit}


class TriangleCalculator:
    def __init__(self):
        self.log_file = open('log_file.csv', mode='a')
        self.triangles = [
            Triangle('IRT', 'USDT', 'NOT'),
            Triangle('IRT', 'USDT', 'METIS'),
        ]

    def calculate(self, market_repo: MarketRepository):
        print("CALCING")
        writer = csv.writer(self.log_file)
        for triangle in self.triangles:
            res = triangle.get_profit_ask_bid(market_repo)

            if res is not None:
                writer.writerow(res.values())

        self.log_file.flush()
