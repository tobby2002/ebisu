# coding: UTF-8

from src import logger
from src.bitmex import BitMex

# STUB 거래용 클래스
class BitMexStub(BitMex):
    # 디폴트 잔액 (0.1BTC)
    balance = 0.1 * 100000000
    # 디롶트 레버리지
    leverage = 1
    # 현재 포지션 사이즈
    position_size = 0
    # 현재 포지션 평균가
    position_avg_price = 0
    # 주문카운트
    order_count = 0
    # 익절카운트
    win_count = 0
    # 손절카운트
    lose_count = 0
    # 익절 총이익
    win_profit = 0
    # 손절 총손해
    lose_loss = 0
    # 최대손실율(MDD)
    max_draw_down = 0
    # 주문
    open_orders = []

    def __init__(self, threading=True):
        """
        컨스트럭터
        :param threading:
        """
        BitMex.__init__(self, threading=threading)

    def get_lot(self):
        """
         주문수량 취득
         :return:
         """
        return int((1 - self.get_retain_rate()) * self.get_balance() / 100000000 * self.get_leverage() * self.get_market_price())

    def get_balance(self):
        """
        잔고 취득
        :return:
        """
        return self.balance

    def get_leverage(self):
        """
        레버리지 취득
        :return:
        """
        return self.leverage

    def get_position_size(self):
        """
         현재 포지션 사이즈 취득
         :return:
         """
        return self.position_size

    def get_position_avg_price(self):
        """
        현재 포지션 평균가격 취득
        :return:
        """
        return self.position_avg_price

    def cancel_all(self):
        """
        모든 주문 취소
        """
        self.open_orders = []

    def close_all(self):
        """
        모든 포지션 해제
        """
        pos_size = self.position_size
        if pos_size == 0:
            return
        long = pos_size < 0
        ord_qty = abs(pos_size)
        self.commit(id, long, ord_qty, self.get_market_price(), True)

    def cancel(self, id):
        """
        주문 취소
        :param long: 롱 or 숏
        :return 成功したか:
        """
        self.open_orders = [o for o in self.open_orders if o["id"] != id]
        return True

    def entry(self, id, long, qty, limit=0, stop=0, post_only=False, when=True):
        """
        주문넣기. pine언어와 동등。
        https://kr.tradingview.com/study-script-reference/#fun_strategy{dot}entry
        :param id: 주문번호
        :param long: 롱 or 숏
        :param qty: 주문수량
        :param limit: 제시가
        :param stop: Stop제시가
        :param post_only: post only 옵션
        :param when: 주문조건
        :return:
        """
        if not when:
            return

        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        self.cancel(id)
        ord_qty = qty + abs(pos_size)

        if limit > 0 or stop > 0:
            self.open_orders.append({"id": id, "long": long, "qty": ord_qty, "limit": limit, "stop": stop, "post_only": post_only})
        else:
            self.commit(id, long, ord_qty, self.get_market_price(), True)
            return

    def commit(self, id, long, qty, price, need_commission=True):
        """
        커밋
        :param id: 주문번호
        :param long: 롱 or 숏
        :param qty: 주문수량
        :param price: 가격
        :param need_commission: 수수료 적용여부
        """
        self.order_count += 1

        order_qty = qty if long else -qty
        next_qty = self.get_position_size() + order_qty
        commission = self.get_commission() if need_commission else 0.0

        if (self.get_position_size() > 0 >= order_qty) or (self.get_position_size() < 0 < order_qty):
            if self.get_position_avg_price() > price:
                close_rate = ((self.get_position_avg_price() - price) / price - commission) * self.get_leverage()
                profit = -1 * self.get_position_size() * close_rate
            else:
                close_rate = ((price - self.get_position_avg_price()) / self.get_position_avg_price() - commission) * self.get_leverage()
                profit = self.get_position_size() * close_rate

            if profit > 0:
                self.win_profit += profit/self.get_market_price()*100000000
                self.win_count += 1
            else:
                self.lose_loss += -1 * profit/self.get_market_price()*100000000
                self.lose_count += 1
                if close_rate > self.max_draw_down:
                    self.max_draw_down = close_rate

            self.balance += profit/self.get_market_price()*100000000

            if self.enable_trade_log:
                logger.info(f"========= Close Position =============")
                logger.info(f"TRADE COUNT   : {self.order_count}")
                logger.info(f"POSITION SIZE : {self.position_size}")
                logger.info(f"ENTRY PRICE   : {self.position_avg_price}")
                logger.info(f"EXIT PRICE    : {price}")
                logger.info(f"PROFIT        : {profit}")
                logger.info(f"BALANCE       : {self.get_balance()}")
                logger.info(f"WIN RATE      : {0 if self.order_count == 0 else self.win_count/self.order_count*100} %")
                logger.info(f"PROFIT FACTOR : {self.win_profit if self.lose_loss == 0 else self.win_profit/self.lose_loss}")
                logger.info(f"MAX DRAW DOWN : {self.max_draw_down * 100}")
                logger.info(f"======================================")

        if next_qty != 0:
            if self.enable_trade_log:
                logger.info(f"********* Create Position ************")
                logger.info(f"TIME          : {self.now_time()}")
                logger.info(f"PRICE         : {price}")
                logger.info(f"TRADE COUNT   : {self.order_count}")
                logger.info(f"ID            : {id}")
                logger.info(f"POSITION SIZE : {qty}")
                logger.info(f"**************************************")

            self.position_size = next_qty
            self.position_avg_price = price
            self.set_trail_price(price)
        else:
            self.position_size = 0
            self.position_avg_price = 0

    def eval_exit(self):
        """
        익손, 손절전략 평가
        """
        if self.get_position_size() == 0:
            return

        price = self.get_market_price()

        # trail asset 가 설정되어 있을 경우
        if self.get_exit_order()['trail_offset'] > 0 and self.get_trail_price() > 0:
            trail_offset = self.get_exit_order()['trail_offset']
            trail_price = self.get_trail_price()
            if self.get_position_size() > 0 and \
                    price - trail_offset < trail_price:
                logger.info(f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}")
                self.close_all()
            elif self.get_position_size() < 0 and \
                    price + trail_offset > trail_price:
                logger.info(f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}")
                self.close_all()

        if self.get_position_avg_price() > price:
            close_rate = ((self.get_position_avg_price() - price) / price - self.get_commission()) * self.get_leverage()
            unrealised_pnl = -1 * self.get_position_size() * close_rate
        else:
            close_rate = ((price - self.get_position_avg_price()) / self.get_position_avg_price() - self.get_commission()) * self.get_leverage()
            unrealised_pnl = self.get_position_size() * close_rate

        # loss 가 설정되어 있을 경우
        if unrealised_pnl < 0 and \
                0 < self.get_exit_order()['loss'] < abs(unrealised_pnl):
            logger.info(f"Loss cut by stop loss: {self.get_exit_order()['loss']}")
            self.close_all()

        # profit 가 설정되어 있을 경우
        if unrealised_pnl > 0 and \
                0 < self.get_exit_order()['profit'] < abs(unrealised_pnl):
            logger.info(f"Take profit by stop profit: {self.get_exit_order()['profit']}")
            self.close_all()

    def on_update(self, bin_size, strategy):
        """
        전략함수 등록
        :param strategy:
        """
        def __override_strategy(open, close, high, low, volume):
            new_open_orders = []

            if self.get_position_size() > 0 and low[-1] > self.get_trail_price():
                self.set_trail_price(low[-1])
            if self.get_position_size() < 0 and high[-1] < self.get_trail_price():
                self.set_trail_price(high[-1])

            for _, order in enumerate(self.open_orders):
                id = order["id"]
                long = order["long"]
                qty = order["qty"]
                limit = order["limit"]
                stop = order["stop"]
                post_only = order["post_only"]

                if limit > 0 and stop > 0:
                    if (long and high[-1] > stop and close[-1] < limit) or (not long and low[-1] < stop and close[-1] > limit):
                        self.commit(id, long, qty, limit, False)
                        continue
                    elif (long and high[-1] > stop) or (not long and low[-1] < stop):
                        new_open_orders.append({"id": id, "long": long, "qty": qty, "limit": limit, "stop": 0})
                        continue
                elif limit > 0:
                    if (long and low[-1] < limit) or (not long and high[-1] > limit):
                        self.commit(id, long, qty, limit, False)
                        continue
                elif stop > 0:
                    if (long and high[-1] > stop) or (not long and low[-1] < stop):
                        self.commit(id, long, qty, stop, False)
                        continue

                new_open_orders.append(order)

            self.open_orders = new_open_orders
            strategy(open, close, high, low, volume)
            self.eval_exit()

        BitMex.on_update(self, bin_size, __override_strategy)
