import logging
import requests
import time
import typing

from urllib.parse import urlencode

import hmac
import hashlib

import base64

import websocket
import json

import threading

from models import *


logger = logging.getLogger()


class KuCoinClient:
    def __init__(self, public_key: str, secret_key: str, pass_phrase: str, sandbox: bool):
        if sandbox:
            self._base_url = "https://api-sandbox-futures.kucoin.com"
        else:
            self._base_url = "https://api.kucoin.com"

        self._public_key = public_key
        self._secret_key = secret_key
        self._pass_phrase = self._b64_encode_string(pass_phrase)

        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()

        logger.info("KuCoin Client successfully initialized")

    def _generate_signature(self, expires: str, method: str, endpoint: str, data: typing.Dict) -> bytes:
        message = expires + method + endpoint + "?" + urlencode(data) if len(data) > 0 else expires + method + endpoint

        return base64.b64encode(hmac.new(self._secret_key.encode(), message.encode(), hashlib.sha256).digest())

    def _b64_encode_string(self, string: str) -> bytes:
        return base64.b64encode(hmac.new(self._secret_key.encode(), string.encode(), hashlib.sha256).digest())

    def _make_request(self, method: str, endpoint: str, data: typing.Dict):
        headers = dict()
        expires = str(int(time.time()) * 1000)

        headers["KC-API-SIGN"] = self._generate_signature(expires, method, endpoint, data)
        headers["KC-API-TIMESTAMP"] = expires
        headers["KC-API-KEY"] = self._public_key
        headers["KC-API-PASSPHRASE"] = self._pass_phrase
        headers["KC-API-KEY-VERSION"] = "2"

        if method == "GET":
            try:
                response = requests.get(self._base_url + endpoint, headers=headers, params=data)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None
        else:
            raise ValueError

        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error while making %s request to %s: %s (error code %s)",
                         method, endpoint, response.json(), response.status_code)
            return None

    def get_contracts(self) -> typing.Dict[str, Contract]:
        symbols = self._make_request("GET", "/api/v1/contracts/active", dict())
        contracts = dict()
        if symbols is not None:
            for s in symbols['data']:
                contracts[s['symbol']] = Contract(s, "kuCoin")

        return contracts

    def get_balances(self, currency: str = 'XBT') -> typing.Dict[str, Balance]:
        data = dict()
        data['currency'] = currency

        margin_data = self._make_request("GET", "/api/v1/account-overview", data)

        balances = dict()

        if margin_data is not None:
            balances[currency] = Balance(margin_data['data'], "kuCoin")

        return balances


