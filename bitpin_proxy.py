from typing import Literal

import requests

BITPIN_URL = 'https://api.bitpin.ir'
BITPIN_API_KEY = '<KEY>'
BITPIN_SECRET_KEY = '<KEY>'


class BitPinProxy:
    def __init__(self):
        self.base_url = BITPIN_URL

    def get_open_orders(self, market_id, order_type: Literal['buy', 'sell'] = 'buy'):
        url_tmpl = f'{self.base_url}/v2/mth/actives/{market_id}/?type={order_type}'

        return requests.get(url_tmpl).json()

bitpin_proxy = BitPinProxy()
