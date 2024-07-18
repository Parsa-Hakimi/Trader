import logging
import os
from typing import Literal

import requests

from utils import get_market_base_and_quote
from order import Order

BITPIN_URL = 'https://api.bitpin.ir'
BITPIN_API_KEY = os.environ.get('BITPIN_API_KEY')
BITPIN_SECRET_KEY = os.environ.get('BITPIN_SECRET_KEY')

logger = logging.getLogger(__name__)


class BitpinProxy:
    def __init__(self):
        self.base_url = BITPIN_URL
        self.access_token = ''
        self.refresh_token = ''

    def _send_request(self, path, method='get', body=None, authenticated=False):
        logger.info("Sending request. path=(%s)", path)
        url = f'{self.base_url}{path}'

        request_method = getattr(requests, method.lower())

        headers = {}
        if authenticated:
            self._ensure_access()
            headers['Authorization'] = f'Bearer {self.access_token}'

        resp = request_method(url, json=body, headers=headers)
        if resp.status_code in [401, 403]:
            logger.info("Request failed. Retrying...")
            self.refresh()
            headers['Authentication'] = f'Bearer {self.access_token}'
            logger.info("Resending request. path=(%s)", path)
            resp = request_method(url, json=body, headers=headers)

        return resp

    def _ensure_access(self):
        if not self.access_token:
            if self.refresh_token:
                self.refresh()
            else:
                self.login()

    def login(self):
        logger.info("Calling login.")
        resp_body = self._send_request('/v1/usr/api/login/', method='post', body={
            'api_key': BITPIN_API_KEY,
            'secret_key': BITPIN_SECRET_KEY,
        }).json()

        self.access_token = resp_body['access']
        self.refresh_token = resp_body['refresh']

    def refresh(self):
        logger.info("Calling refresh.")
        resp = self._send_request('/v1/usr/refresh_token/', method='post', body={
            'refresh': self.refresh_token,
        })

        if resp.status_code >= 300:
            logger.info(f"Refresh failed({resp.status_code}). Logging in again.")
            self.login()
        else:
            self.access_token = resp.json()['access']

    def get_open_orders(self, market_id, order_type: Literal['buy', 'sell'] = 'buy'):
        url_tmpl = f'/v2/mth/actives/{market_id}/?type={order_type}'

        return self._send_request(url_tmpl).json()

    def get_my_open_orders(self):
        orders = []
        resp = self._send_request('/v1/odr/orders/?state=active', authenticated=True).json()
        for order in resp['results']:
            orders.append(Order(
                market=get_market_base_and_quote(order['market']['id']),
                identifier=order['identifier'],
                amount=float(order['remain_amount']),
                price=float(order['price']),
                side=order['type'],
            ))
        return orders

    def get_wallet_info(self):
        path = '/v1/wlt/wallets/'
        resp = self._send_request(path, authenticated=True).json()
        wallet = {}
        for token_info in resp:
            logger.info("TOKEN INFO: %s", str(token_info))
            wallet[token_info['currency']['code']] = float(token_info['total'])
            # TODO: there is also a 'frozen' key and a 'total' key, what are they?
        return wallet

    def place_order(
            self,
            market_id: int,
            base_amount: float,
            price: float,
            side: Literal['buy', 'sell'],
            mode='limit',
            identifier=None,
    ):
        logger.info("Posting order")
        if mode != 'limit':
            raise NotImplementedError

        url = '/v1/odr/orders/'
        payload = {
            'market': market_id,
            'amount1': base_amount,
            # 'amount2': 0,
            'price': price,
            'mode': 'limit',
            'type': side,
            # 'identifier': '',  # TODO: we may need this later
            'price_limit': price,
            # 'price_stop': 0,
            # 'price_limit_oco': 0,
        }

        if identifier is not None:
            payload['identifier'] = identifier

        resp = self._send_request(url, method='post', body=payload, authenticated=True)

        # TODO: Error handling
        return resp.json()


bitpin_proxy = BitpinProxy()
