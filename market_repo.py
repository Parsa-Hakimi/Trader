import json
from collections import defaultdict
from datetime import datetime

import websocket

import metrics
from bitpin_proxy import bitpin_proxy
from utils import MARKET_MAPPING

BITPIN_WS_ADDR = 'wss://ws.bitpin.org'

websocket.setdefaulttimeout(20)


class MarketRepository:
    def __init__(self, u=False):
        self.data = {}
        self.market_prices = defaultdict(dict)
        self.callbacks = []

        self.ws = websocket.WebSocketApp(BITPIN_WS_ADDR,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close)
        self.ws.on_open = self._on_open

        if u:
            self.update_by_order_list()

    def only_data(self):
        m = MarketRepository()
        m.data = self.data
        m.market_prices = self.market_prices
        m.ws = None
        return m

    def handle_currency_price_info_update_event(self, bitpin_resp: dict):
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
        print("Running market repo")
        self.ws.run_forever(
            ping_interval=10,
            ping_payload='{ "message" : "PING"}'
        )

    def _on_message(self, ws, message):
        print(f"Received message: {message[:50]}")
        data = json.loads(message)
        match data.get("event"):
            case "market_update":
                self.handle_market_update_event(data)
            # case "currency_price_info_update":
            #     self.handle_currency_price_info_update_event(data)

    def _on_error(self, ws, error: Exception):
        print(f"Encountered error: {error}")
        import traceback
        traceback.print_exception(error)

    def _on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")

    def _on_open(self, ws):
        print("Connection opened")
        self.ws.send(f'{{"method":"sub_to_market_list", "ids":[{",".join(str(i) for i in MARKET_MAPPING.values())}]}}')

    def handle_market_update_event(self, data):
        event_time = data.get('event_time')

        if event_time:
            if event_time[-1] == 'Z':
                event_time = event_time[:-1]

            event_delay = (datetime.fromisoformat(event_time) - datetime.now()).total_seconds()
            metrics.market_update_delay.labels(market=data['market']['code']).observe(event_delay)

        market_id = int(data['market']['id'])
        sorted_bids = sorted(data['buy'], key=lambda order: float(order['price']), reverse=True)
        sorted_asks = sorted(data['sell'], key=lambda order: float(order['price']))
        updated = False
        if self.market_prices.get(market_id, {}).get('best_bid') != sorted_bids[0]:
            print(f'new best bid: \n{self.market_prices.get(market_id, {}).get("best_bid")} \n{sorted_bids[0]}')
            best_bid: dict = sorted_bids[0].copy()
            best_bid['update_time'] = datetime.now()
            self.market_prices[market_id]['best_bid'] = best_bid
            metrics.best_price.labels(market=data['market']['code'], type='bid').set(float(best_bid.get('price')))
            metrics.best_amount.labels(market=data['market']['code'], type='bid').set(
                float(best_bid.get('remain')))
            updated = True
        if self.market_prices.get(market_id, {}).get('best_ask') != sorted_asks[0]:
            print(f'new best ask: \n{self.market_prices.get(market_id, {}).get("best_ask")} \n{sorted_asks[0]}')
            best_ask: dict = sorted_asks[0].copy()
            best_ask['update_time'] = datetime.now()
            self.market_prices[market_id]['best_ask'] = best_ask
            metrics.best_price.labels(market=data['market']['code'], type='ask').set(float(best_ask.get('price')))
            metrics.best_amount.labels(market=data['market']['code'], type='ask').set(
                float(best_ask.get('remain')))
            updated = True

        if updated:
            self._call_callbacks(market_id)

    def _call_callbacks(self, market_id: int):
        for cb in self.callbacks:
            cb(self, market_id=market_id)
