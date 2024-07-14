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

    def post_order(
            self,
            market_id: int,
            base_amount: float,
            price: float,
            position: Literal['buy', 'sell'],
            mode='limit'
    ):
        if mode != 'limit':
            raise NotImplementedError

        url_tmpl = f'{self.base_url}/v1/odr/orders/'
        payload = {
            'market': market_id,
            'amount1': base_amount,
            # 'amount2': 0,
            'price': price,
            'mode': 'limit',
            'type': position,
            # 'identifier': '',  # TODO: we may need this later
            'price_limit': price,
            # 'price_stop': 0,
            # 'price_limit_oco': 0,
        }

        return requests.post(url_tmpl, json=payload).json()


bitpin_proxy = BitPinProxy()
