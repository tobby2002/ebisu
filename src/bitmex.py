# coding: UTF-8

import json
import math
import os
import traceback
from datetime import datetime, timezone
import time

import pandas as pd
from bravado.exception import HTTPNotFound
from pytz import UTC

from src import logger, retry, allowed_range, to_data_frame, \
    resample, delta, FatalError, notify, ord_suffix
from src.bitmex_api import bitmex_api
from src.bitmex_websocket import BitMexWs


# 本番取引用クラス
from src.orderbook import OrderBook


class BitMex:
    # wallet
    wallet = None
    # 가격
    market_price = 0
    # 포지션
    position = None
    # 마진
    margin = None
    # 이용하는 봉시간 단위
    bin_size = '1h'
    # 개인API사용자
    private_client = None
    # 공개API사용자
    public_client = None
    # 기동중
    is_running = True
    # 봉, 거래량을 취득하는 크롤러
    crawler = None
    # 전략실시 리스너
    strategy = None
    # 로그출력
    enable_trade_log = True
    # OHLC길이
    ohlcv_len = 100
    # OHLC캐쉬
    data = None
    # 이익 확인 손절 구분자
    exit_order = {'profit': 0, 'loss': 0, 'trail_offset': 0}
    # Trailing Stop 가격 봉의 축가격
    trail_price = 0
    # 最後に戦略を実行した時間
    last_action_time = None

    def __init__(self, demo=False, threading=True):
        """
        컨스트럭터
        :param demo:
        :param run:
        """
        self.demo = demo
        self.is_running = threading

    def __init_client(self):
        """
        초기화 함수
        """
        if self.private_client is not None and self.public_client is not None:
            return
        # api_key = os.environ.get("BITMEX_TEST_APIKEY") if self.demo else os.environ.get("BITMEX_APIKEY")
        # api_secret = os.environ.get("BITMEX_TEST_SECRET") if self.demo else os.environ.get("BITMEX_SECRET")
        # tobby2002
        api_key = 'KQW_2f_brKDMjonpBTkBC8nK'
        api_secret = 'NQ2mXkIWNVClJddk0t3ZdO1jV9Ihq39ISV5DLT1pwcU1ZGpt'
        # redlee80
        # api_key = 'NPo11uetPveJeDUMcMW19B_x'
        # api_secret = 'pcbKMRlLxH_fS3oCyEeDkFNhp1UGmyu8CpxLbwEokOvpd2Ud'

        self.private_client = bitmex_api(test=self.demo, api_key=api_key, api_secret=api_secret)
        self.public_client = bitmex_api(test=self.demo)

    def now_time(self):
        """
        현재시간
        """
        return datetime.now().astimezone(UTC)

    def get_retain_rate(self):
        """
        증거금 유지율
        :return:
        """
        return 0.8

    def get_lot(self):
        """
        수량 계산 및 취득
        :return:
        """
        margin = self.get_margin()
        position = self.get_position()
        if margin and position:
            return math.floor((1 - self.get_retain_rate()) * self.get_market_price()
                              * margin['excessMargin'] / (position['initMarginReq'] * 100000000))
        else:
            # logger.info("Error---> There is no margin or no position.")  # 거래내역이 없으면 생기는것 같다.
            return 0
    def get_balance(self):
        """
        잔고 취득
        :return:
        """
        self.__init_client()
        return self.get_margin()["walletBalance"]

    def get_margin(self):
        """
        마진 취득
        :return:
        """
        self.__init_client()
        if self.margin is not None:
            return self.margin
        else:  # WebSocketで取得できていない場合
            self.margin = retry(lambda: self.private_client
                                .User.User_getMargin(currency="XBt").result())
            return self.margin

    def get_leverage(self):
        """
        레버리지 취득
        :return:
        """
        self.__init_client()
        return self.get_position()["leverage"]

    def get_position(self):
        """
        현재포지션 취득
        :return:
        """
        self.__init_client()
        if self.position is not None:
            return self.position
        else:  # WebSocketで取得できていない場合
            ret = retry(lambda: self.private_client
                                  .Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result())
            if len(ret) > 0:
                self.position = ret[0]
            return self.position

    def get_position_size(self):
        """
        현재 포지션 사이즈 취득
        :return:
        """
        self.__init_client()
        return self.get_position()['currentQty']


    def get_whichpositon(self):
        """
        현재 포지션 유무체크
        :return:
        """
        self.__init_client()
        if self.get_position()['currentQty'] > 1:
            return 'LONG'
        elif self.get_position()['currentQty'] < -1:
            return 'SHORT'
        elif self.get_position()['currentQty'] == 0:
            return None


    def get_position_avg_price(self):
        """
        현재 포지션 평균가 취득
        :return:
        """
        self.__init_client()
        return self.get_position()['avgEntryPrice']

    def get_market_price(self):
        """
        현재 시장가 취득
        :return:
        """
        self.__init_client()
        if self.market_price != 0:
            return self.market_price
        else:  # WebSocketで取得できていない場合
            self.market_price = retry(lambda: self.public_client
                                      .Instrument.Instrument_get(symbol="XBTUSD").result())[0]["lastPrice"]

            return self.market_price

    def get_trail_price(self):
        """
        Trail Price 취득
        :return:
        """
        return self.trail_price

    def set_trail_price(self, value):
        """
        Trail Price 설정
        :return:
        """
        self.trail_price = value

    def get_commission(self):
        """
        수수료 취득
        :return:
        """
        return 0.075 / 100

    def cancel_all(self):
        """
        전체 주문 취소
        """
        self.__init_client()
        orders = retry(lambda: self.private_client.Order.Order_cancelAll().result())
        for order in orders:
            logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                        f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                        f"{order['price']}, {order['stopPx']})")
        logger.info(f"Cancel All Order")

    def close_all(self):
        """
        전체 포지션 해제
        """
        self.__init_client()
        order = retry(lambda: self.private_client.Order.Order_closePosition(symbol="XBTUSD").result())
        logger.info(f"Close Position : (orderID, orderType, side, orderQty, limit, stop) = "
                    f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                    f"{order['price']}, {order['stopPx']})")
        logger.info(f"Close All Position")

    def cancel(self, id):
        """
        주문 취소
        :param id: 주문번호
        :return 성공여부
        """
        self.__init_client()
        order = self.get_open_order(id)
        if order is None:
            return False

        try:
            retry(lambda: self.private_client.Order.Order_cancel(orderID=order['orderID']).result())[0]
        except HTTPNotFound:
            return False
        logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                    f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                    f"{order['price']}, {order['stopPx']})")
        return True

    def __new_order(self, ord_id, side, ord_qty, limit=0, stop=0, post_only=False):
        """
        주문 작성
        """

        try:
            if limit > 0 and post_only:
                ord_type = "Limit"
                retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                  side=side, orderQty=ord_qty, price=limit,
                                                                  execInst='ParticipateDoNotInitiate').result())
            elif limit > 0 and stop > 0:
                ord_type = "StopLimit"
                retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                  side=side, orderQty=ord_qty, price=limit,
                                                                  stopPx=stop).result())
            elif limit > 0:
                ord_type = "Limit"
                retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                  side=side, orderQty=ord_qty, price=limit).result())
            elif stop > 0:
                ord_type = "Stop"
                retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                  side=side, orderQty=ord_qty, stopPx=stop).result())
            elif post_only: # market order with post only
                ord_type = "Limit"
                i = 0
                while True:
                    prices = self.ob.get_prices()
                    limit = prices[1] if side == "Buy" else prices[0]
                    retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                      side=side, orderQty=ord_qty, price=limit,
                                                                      execInst='ParticipateDoNotInitiate').result())
                    time.sleep(1)

                    if not self.cancel(ord_id):
                        break
                    time.sleep(2)
                    i += 1
                    if i > 10:
                        notify(f"Order retry count exceed")
                        break
                self.cancel_all()
            else:
                ord_type = "Market"
                retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                  side=side, orderQty=ord_qty).result())

        except Exception as e:
            logger.error('Exception: __new_order : %s' % e)


        if self.enable_trade_log:
            logger.info(f"========= New Order ==============")
            logger.info(f"ID     : {ord_id}")
            logger.info(f"Type   : {ord_type}")
            logger.info(f"Side   : {side}")
            logger.info(f"Qty    : {ord_qty}")
            logger.info(f"Limit  : {limit}")
            logger.info(f"Stop   : {stop}")
            logger.info(f"======================================")

            notify(f"New Order\nType: {ord_type}\nSide: {side}\nQty: {ord_qty}\nLimit: {limit}\nStop: {stop}")

    def __amend_order(self, ord_id, side, ord_qty, limit=0, stop=0, post_only=False):
        """
        주문 갱신
        """
        try:
            if limit > 0 and stop > 0:
                ord_type = "StopLimit"
                retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                    orderQty=ord_qty, price=limit, stopPx=stop).result())
            elif limit > 0:
                ord_type = "Limit"
                retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                    orderQty=ord_qty, price=limit).result())
            elif stop > 0:
                ord_type = "Stop"
                retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                    orderQty=ord_qty, stopPx=stop).result())
            elif post_only: # market order with post only
                ord_type = "Limit"
                prices = self.ob.get_prices()
                limit = prices[1] if side == "Buy" else prices[0]
                retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                    orderQty=ord_qty, price=limit).result())
            else:
                ord_type = "Market"
                retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                    orderQty=ord_qty).result())
        except Exception as e:
            logger.error('Exception: __amend_order : %s' % e)

        if self.enable_trade_log:
            logger.info(f"========= Amend Order ==============")
            logger.info(f"ID     : {ord_id}")
            logger.info(f"Type   : {ord_type}")
            logger.info(f"Side   : {side}")
            logger.info(f"Qty    : {ord_qty}")
            logger.info(f"Limit  : {limit}")
            logger.info(f"Stop   : {stop}")
            logger.info(f"======================================")

            notify(f"Amend Order\nType: {ord_type}\nSide: {side}\nQty: {ord_qty}\nLimit: {limit}\nStop: {stop}")

    def entry(self, id, long, qty, limit=0, stop=0, post_only=False, when=True):
        """
        주문 엔트리 함수. pine언어와 동등
        https://kr.tradingview.com/study-script-reference/#fun_strategy{dot}entry
        :param id: 주문번호
        :param long: 롱 or 숏
        :param qty: 주문수량
        :param limit: 제시가
        :param stop: 스탑제시가
        :param post_only: post only 옵션
        :param when: 주문조건
        :return:
        """
        self.__init_client()

        if self.get_margin()['excessMargin'] <= 0 or qty <= 0:
            return

        if not when:
            return

        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        ord_qty = qty + abs(pos_size)

        self.order(id, long, ord_qty, limit, stop, post_only, when)

    def order(self, id, long, qty, limit=0, stop=0, post_only=False, when=True):
        """
        주문함수. pine언어와 동등
        https://kr.tradingview.com/study-script-reference/#fun_strategy{dot}order
        :param id: 주문번호
        :param long: 롱 or 숏
        :param qty: 주문수량
        :param limit: 제시가
        :param stop: 스탑제시가
        :param post_only: post only 옵션
        :param when: 주문조건
        :return:
        """
        self.__init_client()

        if self.get_margin()['excessMargin'] <= 0 or qty <= 0:
            return

        if not when:
            return

        side = "Buy" if long else "Sell"
        ord_qty = qty

        order = self.get_open_order(id)
        ord_id = id + ord_suffix() if order is None else order["clOrdID"]

        if order is None:
            self.__new_order(ord_id, side, ord_qty, limit, stop, post_only)
        else:
            self.__amend_order(ord_id, side, ord_qty, limit, stop, post_only)

    def get_open_order(self, id):
        """
        주문휘득
        :param id: 주문번호
        :return:
        """
        self.__init_client()
        open_orders = retry(lambda: self.private_client
                            .Order.Order_getOrders(filter=json.dumps({"symbol": "XBTUSD", "open": True}))
                            .result())
        open_orders = [o for o in open_orders if o["clOrdID"].startswith(id)]
        if len(open_orders) > 0:
            return open_orders[0]
        else:
            return None

    def exit(self, profit=0, loss=0, trail_offset=0):
        """
        익손손절 전략 등록. loss 와 trail_offset 이 둘다 설정되 있으면 trail_offset 가 우선함
        :param profit: 이익 (Tick설정)
        :param loss: 손익 (Tick설정)
        :param trail_offset: Trail Stop 가격 (Tick설정)
        """
        self.exit_order = {'profit': profit, 'loss': loss, 'trail_offset': trail_offset}

    def get_exit_order(self):
        """
        익손손절 전략평가 취득
        """
        return self.exit_order

    def eval_exit(self):
        """
        이익, 손익, 손절 전략의 평가후 포지션 정리 함수
        """
        if self.get_position_size() == 0:
            return

        unrealised_pnl = self.get_position()['unrealisedPnl']

        # trail asset 이 설정되어 있으면
        if self.get_exit_order()['trail_offset'] > 0 and self.get_trail_price() > 0:
            if self.get_position_size() > 0 and \
                    self.get_market_price() - self.get_exit_order()['trail_offset'] < self.get_trail_price():
                logger.info(f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}")
                self.close_all()
            elif self.get_position_size() < 0 and \
                    self.get_market_price() + self.get_exit_order()['trail_offset'] > self.get_trail_price():
                logger.info(f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}")
                self.close_all()

        # loss 가 설정되어 있으면
        if unrealised_pnl < 0 and \
                0 < self.get_exit_order()['loss'] < abs(unrealised_pnl / 100000000):
            logger.info(f"Loss cut by stop loss: {self.get_exit_order()['loss']}")
            self.close_all()

        # profit 이 설정되어 있으면
        if unrealised_pnl > 0 and \
                0 < self.get_exit_order()['profit'] < abs(unrealised_pnl / 100000000):
            logger.info(f"Take profit by stop profit: {self.get_exit_order()['profit']}")
            self.close_all()

    def fetch_ohlcv(self, bin_size, start_time, end_time):
        """
        봉데이터 취득
        :param start_time: 시작시간
        :param end_time: 종료시간
        :return:
        """
        self.__init_client()

        fetch_bin_size = allowed_range[bin_size][0]
        left_time = start_time
        right_time = end_time
        data = to_data_frame([])

        while True:
            source = retry(lambda: self.public_client.Trade.Trade_getBucketed(symbol="XBTUSD", binSize=fetch_bin_size,
                                                                              startTime=left_time, endTime=right_time,
                                                                              count=500, partial=False).result())
            if len(source) == 0:
                break

            source = to_data_frame(source)
            data = pd.concat([data, source], sort=True)

            if right_time > source.iloc[-1].name + delta(fetch_bin_size):
                left_time = source.iloc[-1].name + delta(fetch_bin_size)
                time.sleep(2)
            else:
                break

        return resample(data, bin_size)

    def security(self, bin_size):
        """
        다른 시간축 데이터를 재계산 후, 취득
        """
        return resample(self.data, bin_size)[:-1]

    def __update_ohlcv(self, action, new_data):
        """
        데이타를 취득한 후, 전략을 실행
        """

        if self.data is None:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - self.ohlcv_len * delta(self.bin_size)
            d1 = self.fetch_ohlcv(self.bin_size, start_time, end_time)
            if len(d1) > 0:
                d2 = self.fetch_ohlcv(allowed_range[self.bin_size][0],
                                      d1.iloc[-1].name + delta(allowed_range[self.bin_size][0]), end_time)

                self.data = pd.concat([d1, d2], sort=True)
            else:
                self.data = d1
        else:
            self.data = pd.concat([self.data, new_data], sort=True)

        # 最後の行は不確定情報のため、排除する
        re_sample_data = resample(self.data, self.bin_size)[:-1]

        if self.data.iloc[-1].name == re_sample_data.iloc[-1].name:
            self.data = re_sample_data.iloc[-1 * self.ohlcv_len:, :]

        if self.last_action_time is not None and \
                self.last_action_time == re_sample_data.iloc[-1].name:
            return

        open = re_sample_data['open'].values
        close = re_sample_data['close'].values
        high = re_sample_data['high'].values
        low = re_sample_data['low'].values
        volume = re_sample_data['volume'].values

        try:
            if self.strategy is not None:
                self.strategy(open, close, high, low, volume)
            self.last_action_time = re_sample_data.iloc[-1].name
        except FatalError as e:
            # 致命的エラー
            logger.error(f"Fatal error. {e}")
            logger.error(traceback.format_exc())

            notify(f"Fatal error occurred. Stopping Bot. {e}")
            notify(traceback.format_exc())
            self.stop()
        except Exception as e:
            logger.error(f"An error occurred. {e}")
            logger.error(traceback.format_exc())

            notify(f"An error occurred. {e}")
            notify(traceback.format_exc())

    def __on_update_instrument(self, action, instrument):
        """
         거래가격 갱신
        """
        if 'lastPrice' in instrument:
            self.market_price = instrument['lastPrice']

            # trail price 갱신
            if self.get_position_size() > 0 and \
                    self.market_price > self.get_trail_price():
                self.set_trail_price(self.market_price)
            if self.get_position_size() < 0 and \
                    self.market_price < self.get_trail_price():
                self.set_trail_price(self.market_price)

    def __on_update_wallet(self, action, wallet):
        """
         wallet 갱신
        """
        self.wallet = {**self.wallet, **wallet} if self.wallet is not None else self.wallet

    def __on_update_position(self, action, position):
        """
         포지션 갱신
        """
        # 포지션 사이즈 변경이 있었는지 체크
        is_update_pos_size = self.get_position()['currentQty'] != position['currentQty']

        # 포지션 사이즈가 변경된 경우, Trail 개시가격을 현재의 가격에 리셋한다.
        if is_update_pos_size and position['currentQty'] != 0:
            self.set_trail_price(self.market_price)

        if is_update_pos_size:
            logger.info(f"Updated Position\n"
                        f"Price: {self.get_position()['avgEntryPrice']} => {position['avgEntryPrice']}\n"
                        f"Qty: {self.get_position()['currentQty']} => {position['currentQty']}\n"
                        f"Balance: {self.get_balance()/100000000} XBT")
            notify(f"Updated Position\n"
                   f"Price: {self.get_position()['avgEntryPrice']} => {position['avgEntryPrice']}\n"
                   f"Qty: {self.get_position()['currentQty']} => {position['currentQty']}\n"
                   f"Balance: {self.get_balance()/100000000} XBT")

        self.position = {**self.position, **position} if self.position is not None else self.position

        # 利確損切の評価
        self.eval_exit()

    def __on_update_margin(self, action, margin):
        """
         마진 갱신
        """
        self.margin = {**self.margin, **margin} if self.margin is not None else self.margin

    def on_update(self, bin_size, strategy):
        """
        전략함수 등록
        :param strategy:
        """
        self.bin_size = bin_size
        self.strategy = strategy
        if self.is_running:
            self.ws = BitMexWs(test=self.demo)
            self.ws.bind(allowed_range[bin_size][0], self.__update_ohlcv)
            self.ws.bind('instrument', self.__on_update_instrument)
            self.ws.bind('wallet', self.__on_update_wallet)
            self.ws.bind('position', self.__on_update_position)
            self.ws.bind('margin', self.__on_update_margin)
            self.ob = OrderBook(self.ws)

    def stop(self):
        """
        크롤러 정지
        """
        self.is_running = False
        self.ws.close()

    def show_result(self):
        """
        거래결과보기
        """
        pass

    def plot(self, name, value, color, overlay=True):
        """
        그래프 그리기。
        """
        pass
