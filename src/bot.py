# coding: UTF-8

import sys

from hyperopt import fmin, tpe, STATUS_OK, STATUS_FAIL, Trials

from src import logger, notify
from src.bitmex import BitMex
from src.bitmex_stub import BitMexStub
from src.bitmex_backtest import BitMexBackTest


class Bot:
    # 파라메타
    params = {}
    # 거래소
    exchange = None
    # 봉단위
    bin_size = '1h'
    # 봉기간
    periods = 20
    # ohlcv 길이 (길어 질수록 처리시간 지연이 됨  sma 600의 경우는 600, 1440의 경우는 8초정도 지연)
    # ohlcv = 1440
    ohlcv = 8000
    # 테스트넷 옵션
    test_net = False
    # 벡테스트 옵션
    back_test = False
    # 스터브 옵션
    stub_test = False
    # 하이퍼 옵션
    hyperopt = False

    def __init__(self, bin_size):
        """
        컨스트럭터
        :param bin_size: 봉단위
        :param periods: 봉기간
        """
        self.bin_size = bin_size

    def options(self):
        """
        하이퍼옵션 파라메타탐색 값 취득 함수
        """
        pass

    def resolution(self):
        """
        봉기간 사이즈
        """
        return self.bin_size

    def ohlcv_len(self):
        """
        strategy 전략함수에 넘기는 OHLC 길이
        """
        # return 100
        return self.ohlcv

    def input(self, title, type, defval):
        """
        하이퍼옵션에 넘겨지는 파라메타 및 속성설정
        :param title: 파라메타명
        :param defval: 디폴트값
        :return: 値
        """
        p = {} if self.params is None else self.params
        if title in p:
            return type(p[title])
        else:
            return defval

    def strategy(self, open, close, high, low, volume):
        """
        전략함수로 봇을 작성할때 이 함수를 오버라이드해서 사용
        :param open: 시가
        :param close: 종가
        :param high: 고가
        :param low: 저가
        :param volume: 거래량
        """
        pass

    def params_search(self):
        """
 ˜      파라메타 탐색 함수
        """
        def objective(args):
            logger.info(f"Params : {args}")
            try:
                self.params = args
                self.exchange = BitMexBackTest()
                self.exchange.on_update(self.bin_size, self.strategy)
                profit_factor = self.exchange.win_profit/self.exchange.lose_loss
                logger.info(f"Profit Factor : {profit_factor}")
                ret = {
                    'status': STATUS_OK,
                    'loss': 1/profit_factor
                }
            except Exception as e:
                ret = {
                    'status': STATUS_FAIL
                }

            return ret

        trials = Trials()
        best_params = fmin(objective, self.options(), algo=tpe.suggest, trials=trials, max_evals=200)
        logger.info(f"Best params is {best_params}")
        logger.info(f"Best profit factor is {1/trials.best_trial['result']['loss']}")

    def run(self):
        """
˜       Bot 기동
        """
        if self.hyperopt:
            logger.info(f"Bot Mode : Hyperopt")
            self.params_search()
            return

        elif self.stub_test:
            logger.info(f"Bot Mode : Stub")
            self.exchange = BitMexStub()
        elif self.back_test:
            logger.info(f"Bot Mode : Back test")
            self.exchange = BitMexBackTest()
        else:
            logger.info(f"Bot Mode : Trade")
            self.exchange = BitMex(demo=self.test_net)

        self.exchange.ohlcv_len = self.ohlcv_len()
        self.exchange.on_update(self.bin_size, self.strategy)

        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")
        logger.info(f"Resolution : {self.resolution()}")
        logger.info(f"Balance : {self.exchange.get_balance()}")

        notify(f"Starting Bot\n"
                f"Strategy : {type(self).__name__}\n"
                f"Resolution : {self.resolution()}\n"
                f"Balance : {self.exchange.get_balance()/100000000} XBT")

        self.exchange.show_result()

    def stop(self):
        """
˜       Bot 정지 및 Open되어 있는 주문을 취소
        """
        if self.exchange is None:
            return

        logger.info(f"Stopping Bot")

        self.exchange.stop()
        self.exchange.cancel_all()
        sys.exit()
