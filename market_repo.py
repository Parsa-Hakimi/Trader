import json

import websocket

BITPIN_WS_ADDR = 'wss://ws.bitpin.ir'

MARKET_MAPPING= {
    ('USDT', 'IRT'): 5,
    ('NOT', 'IRT'): 772,
    ('NOT', 'USDT'): 773,
    ('METIS', 'IRT'): 365,
    ('METIS', 'USDT'): 366,
}


class MarketRepository:
    def __init__(self):
        self.data = {}
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

    def run(self):
        self.ws.run_forever(ping_interval=10, ping_timeout=9, ping_payload='{ "message" : "PING"}')

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
