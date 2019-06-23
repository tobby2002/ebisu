# coding: UTF-8
import hashlib
import hmac
import json
import os
import threading
import time
import traceback
import urllib

import websocket
from datetime import datetime

from src import logger, to_data_frame, notify


def generate_nonce():
    return int(round(time.time() * 1000))

def generate_signature(secret, verb, url, nonce, data):
    """Generate a request signature compatible with BitMEX."""
    # Parse the url so we can remove the base and extract just the path.
    parsedURL = urllib.parse.urlparse(url)
    path = parsedURL.path
    if parsedURL.query:
        path = path + '?' + parsedURL.query

    # print "Computing HMAC: %s" % verb + path + str(nonce) + data
    message = (verb + path + str(nonce) + data).encode('utf-8')

    signature = hmac.new(secret.encode('utf-8'), message, digestmod=hashlib.sha256).hexdigest()
    return signature


class BitMexWs:
    # 테스트넷
    testnet = False
    # 가동상태
    is_running = True
    # 보고용 리스너
    handlers = {}
    
    def __init__(self, test=False):
        """
        컨스트럭터
        """
        self.testnet = test
        if test:
            domain = 'testnet.bitmex.com'
        else:
            domain = 'www.bitmex.com'
        self.endpoint = 'wss://' + domain + '/realtime?subscribe=tradeBin1m:XBTUSD,' \
                        'tradeBin5m:XBTUSD,tradeBin1h:XBTUSD,tradeBin1d:XBTUSD,instrument:XBTUSD,' \
                        'margin,position:XBTUSD,wallet,orderBookL2:XBTUSD'
        self.ws = websocket.WebSocketApp(self.endpoint,
                             on_message=self.__on_message,
                             on_error=self.__on_error,
                             on_close=self.__on_close,
                             header=self.__get_auth())
        self.wst = threading.Thread(target=self.__start)
        self.wst.daemon = True
        self.wst.start()

    def __get_auth(self):
        """
        인증정보 설정
        """
        # api_key = os.environ.get("BITMEX_TEST_APIKEY") if self.testnet else os.environ.get("BITMEX_APIKEY")
        # api_secret = os.environ.get("BITMEX_TEST_SECRET") if self.testnet else os.environ.get("BITMEX_SECRET")
        # tobby
        # api_key = 'KQW_2f_brKDMjonpBTkBC8nK'
        # api_secret = 'NQ2mXkIWNVClJddk0t3ZdO1jV9Ihq39ISV5DLT1pwcU1ZGpt'
        # redlee
        api_key = 'NPo11uetPveJeDUMcMW19B_x'
        api_secret = 'pcbKMRlLxH_fS3oCyEeDkFNhp1UGmyu8CpxLbwEokOvpd2Ud'

        if len(api_key) > 0 and len(api_secret):
            nonce = generate_nonce()
            return [
                "api-nonce: " + str(nonce),
                "api-signature: " + generate_signature(api_secret, 'GET', '/realtime', nonce, ''),
                "api-key:" + api_key
            ]
        else:
            logger.info("WebSocket is not authenticating.")
            return []

    def __start(self):
        """
        WebSocket 개시
        """
        while self.is_running:
            self.ws.run_forever()

    def __on_error(self, ws, message):
        """
        WebSokcet 에러발생시
        :param ws:
        :param message:
        """
        logger.error(message)
        logger.error(traceback.format_exc())

        notify(f"Error occurred. {message}")
        notify(traceback.format_exc())

    def __on_message(self, ws, message):
        """
        새로운 데이터를 취득시
        :param ws:
        :param message:
        :return:
        """
        try:
            obj = json.loads(message)
            if 'table' in obj:
                if len(obj['data']) <= 0:
                    return

                table = obj['table']
                action = obj['action']
                data = obj['data']

                if table.startswith("tradeBin"):
                    data[0]['timestamp'] = datetime.strptime(data[0]['timestamp'][:-5], '%Y-%m-%dT%H:%M:%S')
                    self.__emit(table, action, to_data_frame([data[0]]))

                elif table.startswith("instrument"):
                    self.__emit(table, action, data[0])

                elif table.startswith("margin"):
                    self.__emit(table, action, data[0])

                elif table.startswith("position"):
                    self.__emit(table, action, data[0])

                elif table.startswith("wallet"):
                    self.__emit(table, action, data[0])

                elif table.startswith("orderBookL2"):
                    self.__emit(table, action, data)

        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    def __emit(self, key, action, value):
        """
        데이터 송출
        """
        if key in self.handlers:
            self.handlers[key](action, value)

    def __on_close(self, ws):
        """
        종료시
        :param ws:
        """
        if 'close' in self.handlers:
            self.handlers['close']()

        if self.is_running:
            logger.info("Websocket restart")
            notify(f"Websocket restart")

            self.ws = websocket.WebSocketApp(self.endpoint,
                                 on_message=self.__on_message,
                                 on_error=self.__on_error,
                                 on_close=self.__on_close,
                                 header=self.__get_auth())
            self.wst = threading.Thread(target=self.__start)
            self.wst.daemon = True
            self.wst.start()

    def on_close(self, func):
        """
        종료 보고처 등록
        :param func:
        """
        self.handlers['close'] = func

    def bind(self, key, func):
        """
        새로운 데이터를 보고처에 등록
        :param key:
        :param func:
        """
        if key == '1m':
            self.handlers['tradeBin1m'] = func
        if key == '5m':
            self.handlers['tradeBin5m'] = func
        if key == '1h':
            self.handlers['tradeBin1h'] = func
        if key == '1d':
            self.handlers['tradeBin1d'] = func
        if key == 'instrument':
            self.handlers['instrument'] = func
        if key == 'margin':
            self.handlers['margin'] = func
        if key == 'position':
            self.handlers['position'] = func
        if key == 'wallet':
            self.handlers['wallet'] = func
        if key == 'orderBookL2':
            self.handlers['orderBookL2'] = func

    def close(self):
        """
        종료
        """
        self.is_running = False
        self.ws.close()