# -*- coding: UTF-8 -*-
"""
This file is part of the cvclient package.
Copyright (c) 2021 Kevin Eales.

This program is experimental and proprietary, redistribution is prohibited.
Please see the license file for more details.
------------------------------------------------------------------------------------------------------------------------

This is the public facing API client.

Please note that this system uses transaction chaining and as such you should only init the client once in your code.
    Failure to do so will result in transaction chain breakage and in turn risk key deactivation.
"""

import json
import time
import requests
import urllib3

TRANSACTION_CACHE = dict()


class Client:
    """
    This is a basic API client with super fancy transaction chaining.

    """

    def __init__(self, key: str, host: str, verify: bool = False, debug: bool = False):
        global TRANSACTION_CACHE
        self.verify = verify
        if not self.verify:
            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning)  # Temporary until we stop using self signed certs.
        self.debug = debug
        self.cache = TRANSACTION_CACHE
        self.local_stamp = None
        self.key = key
        self.host = host
        self.request = None
        self.response = None
        self.chart = None
        self.alerts = None
        self.urls = {
            'status': '/client/status',
            'alerts': '/client/alerts',
            'charts': '/client/charts'
        }
        self.allowed_times = [
            '15MINUTE',
            '30MINUTE',
            '1HOUR',
            '4HOUR',
            '1DAY'
        ]
        self.request_types = {
            'aaa': 'aaa_floating'
        }
        for req in self.request_types:
            self.cache[req] = dict()
            self.cache[req]['stamp'] = str()
            self.cache[req]['alerts'] = dict()
            self.cache[req]['charts'] = dict()

    def check_req(self, req: str):
        """
        This ensures we don't have a problematic request type.
        """
        if req not in self.request_types:
            print('no handler for request:', req)
            raise ValueError

    def format_url(self, url: str) -> str:
        """
        This creates a fully formatted URL including keys.
        """
        return self.host + url + '?key=' + self.key

    def send_tx(self):
        """
        This sends our transaction ID.
        :return: Self.
        """
        tx = str()
        if self.key in self.cache.keys():
            tx = self.cache[self.key]
        self.request.update({'tx': tx})
        if self.debug:
            print('client sending transaction ID', tx, '*dbug*')
        return self

    def recv_tx(self):
        """
        This receives our new transaction key and stores it into cache.
        :return: Self.
        """
        if 'tx' in self.response.keys():
            self.cache[self.key] = self.response['tx']
            if self.debug:
                print('client: received transaction ID', self.response['tx'], '*dbug*')
        return self

    def post(self, url_path: str, request: dict):
        """
        Performs a JSON post request.

        Example:

            req = {
                'mappings': {'some': 'mappings'},
                'conf': {'some': 'configs'},
                'payload': {'big': 'payload here'},
                'comp': {'big': 'compare payload here'}
            }
            client = ApiClient('https://127.0.0.1:5000/', 'myapikey')
            response = client.post('api01/y', req).response
            print(response.json()
        """
        self.request = request
        url = self.format_url(url_path)  # Build our request URL.
        self.send_tx()  # Send our transaction ID.
        if self.debug:
            print('sending request:', self.request)
        try:
            self.response = requests.post(url, json=self.request, verify=self.verify)
        except (  # Retry failed connection every 5 seconds.
                urllib3.exceptions.NewConnectionError,
                requests.exceptions.ConnectionError,
                requests.exceptions.InvalidURL,
                AttributeError,
        ) as err:
            print('unable to connect to server', url, '*err*')
            print(err, '*dbug*')
            time.sleep(5)  # Prevent hammer retries.
            print('retrying connection', '*info*')
            self.post(url_path, request)
        try:
            try:
                self.response = self.response.json()  # Get response from api.
            except json.decoder.JSONDecodeError:
                if not self.response.text:
                    print('connection failure, invalid API key')
                    raise ConnectionError
                print('unable to process json response', '*err*')
                raise AttributeError
            self.recv_tx()  # Update transaction ID.
        except AttributeError:
            print('connection error')
            if isinstance(self.response, dict):
                print(self.response)
            time.sleep(5)
            self.post(url_path, request)
        return self

    def check_status(self, req_ty: str, cache_key: str) -> bool:
        """
        This will check to see if new data is available.
        :param req_ty: Requested solver type.
        :param cache_key: Local cache key to check.

        """
        self.check_req(req_ty)
        result = False
        stamp = None
        try:  # Same difference if the key isn't in the cache.
            request = {'status_type': self.request_types[req_ty]}
            if self.debug:
                print('checking key', cache_key)
                print('status request', request)
            self.post(self.urls['status'], request)
            stamp = self.response['stamp']
            if stamp != self.local_stamp or cache_key not in self.cache.keys():
                self.local_stamp = stamp  # Update local timestamp.
                result = True
            if self.debug:
                print('cache:', self.local_stamp, 'returned', stamp, 'result:', result)
                print('keys:', self.cache.keys())
        except KeyError:
            result = True
        if self.debug:
            print('local', self.local_stamp)
            print('remote', stamp)
            print('status result', result)
        return result

    def get_alerts(self, req_ty: str = 'aaa') -> dict:
        """
        This will fetch the latest alerts from our server.

        Example response:
            {
                'tx': '9fd73a9f-6008-4df1-bc60-5c86a0aa0350',
                'alerts': {
                            'bch': [0.08, 0.24, 0.24],
                            'ltc': [0.08, 0.24, 0.24],
                            'etc': [0.08, 0.24, 0.24],
                            'matic': [0.11, 0.31, 0.31],
                            'xrp': [-3.26, -9.78, -9.78],
                            'ada': [-3.04, -9.120000000000001, -9.120000000000001],
                            'doge': [-3.04, -9.120000000000001, -9.120000000000001],
                            'dot': [-3.04, -9.120000000000001, -9.120000000000001],
                            'uni': [-3.04, -9.120000000000001, -9.120000000000001],
                            'btc_eth': [-284.4486, -284.0858, -284.0858],
                            'FGI': 25
                },
                'type': None,
                'msg': None
            }
        :param req_ty: Solver to request
        :return: Response from server (Or cached request values if no new data is available.
        """
        cache_kay = req_ty + 'alerts'
        if self.check_status(req_ty, cache_kay):
            request = {'alert_type': self.request_types[req_ty]}
            response = self.post(self.urls['alerts'], request).response
            self.cache[cache_kay] = response
        else:
            response = self.cache[cache_kay]
        return response

    def get_chart(
            self,
            chart_type: str = 'aaa',
            chart_length: int = 20,
            chart_time: str = '15MINUTE',
            chart_focus: str = str(),
            chart_pair: str = str(),
            include_alerts: str = 'false',
            multiplier: int = 1
    ) -> dict:
        """
        This will get us some tastey chart data.

        Example response:
            {
                'tx': 'e4b29ac7-334b-4016-ae76-8ebfe5f0f7dc',
                'stamp': '2021-07-12-13-55',
                'chart_data': [
                                    [281.84, 282.28, 281.84, 282.28, 0.1814],
                                    [282.28, 282.72, 282.28, 282.72, 0.1814]
                ],
                'price_data': None,
                'alert_data': {
                                    'bch': 0.08,
                                    'ltc': 0.08,
                                    'etc': 0.08,
                                    'matic': 0.08,
                                    'xrp': -3.26,
                                    'ada': -3.04,
                                    'doge': -3.04,
                                    'dot': -3.04,
                                    'uni': -3.04,
                                    'btc_eth': 0.44000000000005457
                                },
                'type': None,
                'msg': None
            }


        :param chart_type: The math solver to acquire the chart info.
        :param chart_length: Number of bars we wish to receive.
        :param chart_time: Chart time sample.
        :param chart_focus: The target currency to sample.
        :param chart_pair: This is an optional pairing that only used if you want binance price data returned.
        :param include_alerts: This will include the latest alert values for this timesample.
        :param multiplier: This will scale the affect the target currency has on the chart formation.
        :return: Response from server (Or cached request values if no new data is available.
        """
        request = {
            'chart_type': self.request_types[chart_type],
            'chart_length': chart_length,
            'chart_time': chart_time,
            'chart_focus': chart_focus,
            'chart_pair': chart_pair,
            'include_alerts': include_alerts,
            'multiplier': multiplier
        }
        specific = str()
        for key in request:
            specific += str(request[key])
        if self.check_status(chart_type, specific):
            response = self.post(self.urls['charts'], request).response
            self.cache[specific] = response
        else:
            response = self.cache[specific]
        return response
