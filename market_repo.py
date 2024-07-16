import json

import rel
import websocket

from bitpin_proxy import bitpin_proxy

BITPIN_WS_ADDR = 'wss://ws.bitpin.ir'

MARKET_MAPPING = {
    ('USDT', 'IRT'): 5,
    ('NOT', 'IRT'): 772,
    ('NOT', 'USDT'): 773,
    ('METIS', 'IRT'): 365,
    ('METIS', 'USDT'): 366,
    ('BTC', 'IRT'): 1,
    ('BTC', 'USDT'): 2,
    ('ETH', 'USDT'): 3,
    ('ETH', 'IRT'): 4,
    ('TON', 'IRT'): 355,
    ('TON', 'USDT'): 356,
    ('DOGE', 'IRT'): 62,
    ('DOGE', 'USDT'): 63,
}

websocket.setdefaulttimeout(20)

class MarketRepository:
    def __init__(self):
        self.data = {}
        self.market_prices = {}
        self.callbacks = []

        self.ws = websocket.WebSocketApp(BITPIN_WS_ADDR,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close)
        self.ws.on_open = self._on_open

    def update(self, bitpin_resp: dict):
        self.data = bitpin_resp
        for cb in self.callbacks:
            cb(self)

    def update_by_order_list(self):
        for _, market_id in MARKET_MAPPING.items():
            res = bitpin_proxy.get_open_orders(market_id, 'buy')
            sorted_bids = sorted(res['orders'], key=lambda order: float(order['price']), reverse=True)
            res = bitpin_proxy.get_open_orders(market_id, 'sell')
            sorted_asks = sorted(res['orders'], key=lambda order: float(order['price']))

            self.market_prices[market_id] = {
                'best_bid': sorted_bids[0],
                'best_ask': sorted_asks[0],
            }

    def add_callback(self, f):
        self.callbacks.append(f)

    def get_price(self, base, quote):
        market_id = MARKET_MAPPING.get((base, quote))
        reverse_market_id = MARKET_MAPPING.get((quote, base))

        if market_id is not None:
            return self._get_market_price(market_id)

        if reverse_market_id is not None:
            return 1. / self._get_market_price(reverse_market_id)

        return None

    def _get_market_price(self, market_id):
        if market_id not in self.data:
            market_id = str(market_id)

        return float(self.data[market_id].get('price'))

    def get_market_ask(self, base, quote):
        market_id = MARKET_MAPPING.get((base, quote))
        if market_id not in self.market_prices:
            market_id = str(market_id)

        return self.market_prices[market_id].get('best_ask')

    def get_market_bid(self, base, quote):
        market_id = MARKET_MAPPING.get((base, quote))
        if market_id not in self.market_prices:
            market_id = str(market_id)

        return self.market_prices[market_id].get('best_bid')

    def run(self):
        self.ws.run_forever(
            ping_interval=10,
            ping_payload='{ "message" : "PING"}',
            dispatcher=rel,
            reconnect=5)
        rel.signal(2, rel.abort)
        rel.dispatch()

    def _on_message(self, ws, message):
        print(f"Received message: {message}")
        data = json.loads(message)
        if data.get("event") == 'currency_price_info_update':
            self.update(json.loads(message))

    def _on_error(self, ws, error):
        print(f"Encountered error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")

    def _on_open(self, ws):
        print("Connection opened")
        self.ws.send('{"method":"sub_to_price_info"}')
