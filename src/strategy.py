# coding: UTF-8
import os
import random

import math
import re

import numpy
from hyperopt import hp

from src import highest, lowest, sma, crossover, crossunder, over, under, last, rci, rsi, double_ema, ema, triple_ema, wma, \
    ssma, hull, logger, notify, atr, supertrend
from src.bitmex import BitMex
from src.bitmex_stub import BitMexStub
from src.bot import Bot
from src.gmail_sub import GmailSub

# channel break out
class Doten(Bot):
    def __init__(self):
        Bot.__init__(self, '15m')

    def options(self):
        return {
            'length': hp.randint('length', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        length = self.input('length', int, 9)
        up = last(highest(high, length))
        dn = last(lowest(low, length))
        self.exchange.plot('up', up, 'b')
        self.exchange.plot('dn', dn, 'r')
        self.exchange.entry("Long", True, round(lot / 2), stop=up)
        self.exchange.entry("Short", False, round(lot / 2), stop=dn)


# sma cross
class SMA(Bot):
    def __init__(self):
        Bot.__init__(self, '2h')

    def options(self):
        return {
            'fast_len': hp.quniform('fast_len', 1, 30, 1),
            'slow_len': hp.quniform('slow_len', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        fast_len = self.input('fast_len', int, 9)
        slow_len = self.input('slow_len', int, 16)
        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)
        golden_cross = crossover(fast_sma, slow_sma)
        dead_cross = crossunder(fast_sma, slow_sma)
        if golden_cross:
            self.exchange.entry("Long", True, lot)
        if dead_cross:
            self.exchange.entry("Short", False, lot)

# supertrend
class SuperTrend(Bot):

    prebalance = BitMex(threading=False).get_balance()
    dealcount = 0

    def __init__(self):
        Bot.__init__(self, '15m')

    def options(self):
        return {
            'factor': hp.randint('factor', 1, 30, 1),
            'period': hp.randint('period', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        # for test
        # lot = int(round(lot / 100))

        bitmex = BitMex(threading=False)

        price = bitmex.get_market_price()

        factor = self.input('factor', int, 3)
        period = self.input('period', int, 7)


        atrvar = atr(high, low, close, period=period)
        # up = (high + low) / 2 - (factor * atr(high, low, close, period=period))
        # logger.info('up:%s\n' % up)
        # dn = (high + low) / 2 + (factor * atr(high, low, close, period=period))
        # logger.info('atrvar: %s' % atrvar[-1])

        resolution = self.input(defval=15, title="resolution", type=int) # defval 변경, 예) 5분 --> 5
        source = self.exchange.security(str(resolution) + 'm')  # init  참고
        supertrenddf = supertrend(source, factor, period)

        # logger.info('supertrend:%s' % supertrenddf.describe())
        # logger.info('supertrend:%s' % supertrenddf.columns)

        logger.info('price:%s\n' % price)
        # logger.info('source:%s\n' % source[-1])
        logger.info('supertrend value:%s' % supertrenddf['SuperTrend'][-1])
        logger.info('supertrend Upper Band:%s' % supertrenddf['Upper Band'][-1])
        logger.info('supertrend Lower Band:%s' % supertrenddf['Lower Band'][-1])
        logger.info('supertrenddf[Trend][-1]:%s' % supertrenddf['Trend'][-1])
        logger.info('supertrenddf[TSL][-1]:%s' % supertrenddf['TSL'][-1])
        logger.info('supertrenddf[ATR][-1]:%s' % supertrenddf['ATR'][-1])

        longCondition_supertrend = crossover(close, supertrenddf['SuperTrend']) and close[-1] > supertrenddf['SuperTrend'][-1]
        shortCondition_supertrend = crossunder(close, supertrenddf['SuperTrend']) and close[-1] < supertrenddf['SuperTrend'][-1]


        if longCondition_supertrend:
            self.exchange.entry("Long", True, lot)
            logger.info('longCondition_supertrend:%s\n' % longCondition_supertrend)

        elif shortCondition_supertrend:
            self.exchange.entry("Short", False, lot)
            logger.info('shortCondition_supertrend:%s\n' % shortCondition_supertrend)
        else:
            # self.exchange.close_all()
            logger.info('Condition_supertrend:%s\n' % 'else')


        self.dealcount += 1

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))

        realised_pnl = bitmex.get_margin()['realisedPnl']

        logger.info('dealcount:%s' % self.dealcount)
        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)
        # logger.info('bitmex.get_margin():%s' % bitmex.get_margin())
        # logger.info('bitmex.get_position():%s' % bitmex.get_position())

        # logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        # logger.info('get_pre_prebalance:%s' % get_pre_prebalance(self.prebalance, bitmex.get_balance()))
        #     # self.exchange.close_all()
        #     # self.exchange.cancel_all()

        logger.info('--------------------------------------------------')


class DoubleSuperRSI(Bot): # logic https: // stock79.tistory.com / 177

    prebalance = BitMex(threading=False).get_balance()
    dealcount = 0
    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'length': hp.randint('length', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()

        # for test lot
        lot = int(round(lot / 50))
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()
        position_avg_price = bitmex.get_position_avg_price()

        # variants settings
        rsi2_len = self.input('length', int, 2)
        rsi50_len = self.input('length50', int, 50)
        rsi2 = rsi(close, rsi2_len)
        rsi50 = rsi(close, rsi50_len)

        factor = self.input('factor', int, 3)
        period = self.input('period', int, 7)
        factor2 = self.input('factor2', int, 20)
        period2 = self.input('period2', int, 7)

        resolution = self.input(defval=1, title="resolution", type=int) # defval 변경, 예) 5분 --> 5
        source = self.exchange.security(str(resolution) + 'm')  # def __init__  비교
        supertrenddf = supertrend(source, factor, period)
        supertrenddf2 = supertrend(source, factor2, period2)

        print('supertrenddf:%s' % supertrenddf)
        print('supertrenddf2:%s' % supertrenddf2)

        fast_len = self.input('fast_len', int, 5)
        half_len = self.input('half_len', int, 50)
        slow_len = self.input('slow_len', int, 200)

        fast_sma = sma(close, fast_len)
        half_sma = sma(close, half_len)
        slow_sma = sma(close, slow_len)

        # conditions
        sma_long = over(fast_sma[-1], slow_sma[-1])
        sma_short = under(fast_sma[-1], slow_sma[-1])

        super_long = over(close[-1], supertrenddf['SuperTrend'][-1])
        super_short = under(close[-1], supertrenddf['SuperTrend'][-1])
        supertrendtrend = supertrenddf['Trend'][-1]

        super2_long = over(close[-1], supertrenddf2['SuperTrend'][-1])
        super2_short = under(close[-1], supertrenddf2['SuperTrend'][-1])
        supertrendtrend2 = supertrenddf2['Trend'][-1]

        super_centerline = (supertrenddf['SuperTrend'][-1] + supertrenddf2['SuperTrend'][-1])/2

        rsi2_overbought = over(rsi2[-1], 95)
        rsi2_oversold = under(rsi2[-1], 5)

        rsi50_over = over(rsi50[-1], 50)
        rsi50_under = under(rsi50[-1], 50)

        price_under = under(price, half_sma[-1])
        price_over = over(price, half_sma[-1])

        half_before = over(close[-1], half_sma[-1])
        half_after = under(close[-1], half_sma[-1])

        # show infomations

        logger.info('price: %s' % price)

        logger.info('fast_sma[-1]: %s' % fast_sma[-1])
        logger.info('slow_sma[-1]: %s' % slow_sma[-1])


        logger.info('sma_long: %s' % sma_long)
        logger.info('sma_short: %s' % sma_short)

        logger.info('super_long: %s' % super_long)
        logger.info('super_short: %s' % super_short)
        logger.info('sma_trend: %s\n' % supertrendtrend)



        logger.info('supertrend value:%s' % supertrenddf['SuperTrend'][-1])
        logger.info('supertrend Upper Band:%s' % supertrenddf['Upper Band'][-1])
        logger.info('supertrend Lower Band:%s' % supertrenddf['Lower Band'][-1])
        logger.info('supertrenddf[Trend][-1]:%s' % supertrenddf['Trend'][-1])
        logger.info('supertrenddf[TSL][-1]:%s' % supertrenddf['TSL'][-1])
        logger.info('supertrenddf[ATR][-1]:%s\n' % supertrenddf['ATR'][-1])



        logger.info('supertrend2 value:%s' % supertrenddf2['SuperTrend'][-1])
        logger.info('supertrend2 Upper Band:%s' % supertrenddf2['Upper Band'][-1])
        logger.info('supertrend2 Lower Band:%s' % supertrenddf2['Lower Band'][-1])
        logger.info('supertrenddf2[Trend][-1]:%s' % supertrenddf2['Trend'][-1])
        logger.info('supertrenddf2[TSL][-1]:%s' % supertrenddf2['TSL'][-1])
        logger.info('supertrenddf2[ATR][-1]:%s\n' % supertrenddf2['ATR'][-1])


        logger.info('supertrenddf[SuperTrend][-1]:%s + supertrenddf2[SuperTrend][-1]:%s ' % (supertrenddf['SuperTrend'][-1], supertrenddf2['SuperTrend'][-1]))
        logger.info('super_centerline: %s' % super_centerline)

        logger.info('rsi2[-1 ]%s' % rsi2[-1])
        logger.info('rsi50[-1 ]%s' % rsi50[-1])
        logger.info('rsi2_oversold: %s' % rsi2_oversold)
        logger.info('rsi2_overbought: %s' % rsi2_overbought)

        logger.info('price_under: %s' % price_under)
        logger.info('price_over: %s' % price_over)

        logger.info('half_before: %s' % half_before)
        logger.info('half_after: %s' % half_after)

        logger.info('get_whichpositon(): %s' % bitmex.get_whichpositon())
        logger.info('position_size(): %s' % bitmex.get_position_size())


        # entry
        if super2_long:
            logger.info('+ + + + + LONG + + + + + LONG + + + + + LONG + + + + + ')
            if bitmex.get_whichpositon() is None:  # and (not supertrendtrend and supertrendtrend2) and rsi2_overbought:
                logger.info('postion condition > None')
                if bitmex.get_open_order('Short'):
                    self.exchange.cancel('Short')
                self.exchange.entry("Long", True, lot, limit=math.ceil(super_centerline), post_only=True)

            elif bitmex.get_whichpositon() == 'LONG':
                logger.info('postion condition  > LONG')
                if supertrendtrend and supertrendtrend2 and rsi2_oversold: # closing
                    logger.info('postion condition  > LONG > Closing')
                    self.exchange.order("Long", False, abs(bitmex.get_position_size()), limit=price + 2.5, post_only=True)
                elif rsi2_overbought: # add more entry
                    logger.info('postion condition  > LONG > Rsi2 overbout')
                    self.exchange.entry("LongAdd", True, lot, limit=price - 0.5, post_only=True)
                elif super_short: # stop loss
                    logger.info('postion condition  > LONG > super_short(stop loss)')
                    self.exchange.entry("Long", True, lot)
                    self.exchange.entry("LongAdd", True, lot)
                else:
                    logger.info('postion condition  > LONG > else')
                    self.exchange.order("Long", False, abs(bitmex.get_position_size()), limit=price + 10, post_only=True)


            elif bitmex.get_whichpositon() == 'SHORT':
                logger.info('cancel SHORT on long trend')
                # self.exchange.cancel_all()
                self.exchange.close_all()
                self.exchange.close_all()
            else:

                logger.info('Super Shot --> Else')

        if super2_short:
            logger.info('- - - - - SHORT - - - - - SHORT - - - - - SHORT - - - - - ')
            if bitmex.get_whichpositon() is None:  #and rsi2_overbought and price_over:
                logger.info('postion condition > None')
                if bitmex.get_open_order('Long'):
                    self.exchange.cancel('Long')
                self.exchange.entry("Short", False, lot, limit=math.floor(super_centerline), post_only=True)

            elif bitmex.get_whichpositon() == 'SHORT':
                logger.info('postion condition  > SHORT')

                if price_under:  # closing
                    logger.info('postion condition  > SHORT > price_under(closing)')
                    self.exchange.order("Short", True, abs(bitmex.get_position_size()), limit=price-2.5, when=price_under, post_only=True)
                elif rsi2_oversold:  # add more entry
                    logger.info('postion condition  > SHORT > rsi2_oversold(add more entry)')
                    self.exchange.entry("ShortAdd", False, lot, limit=price - 0.5, post_only=True)
                elif super_long:  # stop loss
                    logger.info('postion condition  > SHORT > super_short(stop loss)')
                    self.exchange.entry("Short", True, lot)
                    self.exchange.entry("ShortAdd", True, lot)
                else:
                    logger.info('postion condition  > SHORT > else')
                    self.exchange.order("Short", True, abs(bitmex.get_position_size()), limit=price - 10, post_only=True)

            elif bitmex.get_whichpositon() == 'LONG':
                logger.info('cancel LONG on short trend')
                self.exchange.close_all()
            else:

                logger.info('Super Shot --> Else')


        self.dealcount += 1

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))

        realised_pnl = bitmex.get_margin()['realisedPnl']

        logger.info('dealcount:%s' % self.dealcount)
        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)

        logger.info('--------------------------------------------------')

# rci
class Rci(Bot):
    def __init__(self):
        Bot.__init__(self, '5m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
            'rcv_medium_len': hp.quniform('rcv_medium_len', 5, 15, 1),
            'rcv_long_len': hp.quniform('rcv_long_len', 10, 20, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        itv_s = self.input('rcv_short_len', int, 5)
        itv_m = self.input('rcv_medium_len', int, 9)
        itv_l = self.input('rcv_long_len', int, 15)

        rci_s = rci(close, itv_s)
        rci_m = rci(close, itv_m)
        rci_l = rci(close, itv_l)

        long = ((-80 > rci_s[-1] > rci_s[-2]) or (-82 > rci_m[-1] > rci_m[-2])) \
               and (rci_l[-1] < -10 and rci_l[-2] > rci_l[-2])
        short = ((80 < rci_s[-1] < rci_s[-2]) or (rci_m[-1] < -82 and rci_m[-1] < rci_m[-2])) \
                and (10 < rci_l[-1] < rci_l[-2])
        close_all = 80 < rci_m[-1] < rci_m[-2] or -80 > rci_m[-1] > rci_m[-2]

        if long:
            self.exchange.entry("Long", True, lot)
        elif short:
            self.exchange.entry("Short", False, lot)
        elif close_all:
            self.exchange.close_all()




# Fibonacci Retracement & Expansion Strategy
class Fibo(Bot):
    prebalance = BitMex(threading=False).get_balance()
    start = 0
    pre_fb0 = 0
    pre_fb100 = 0
    idx = 0
    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
        }

    def strategy(self, open, close, high, low, volume):
        self.start += 1
        flg_changed_timezone = False

        lot = self.exchange.get_lot()
        # for test lot
        # lot = int(round(lot / 20))
        lot = 500
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()


        sma_base_l = self.input('sma_short_len', int, 200)

        resolution = self.input(defval=5, title="resolution", type=int) # defval 변경, 예) 5분 --> 5, 'm' or 1시간  1, 'h', 1Day 1, 'd'
        source = self.exchange.security(str(resolution) + 'm')  # def __init__  비교
        logger.info('source: %s' % source)

        series_high = source['high'].values
        series_low = source['low'].values

        fb100 = last(highest(series_high, 1))  # 1시간 1, 1D의 경우는 resolution도 변경
        fb0 = last(lowest(series_low, 1))

        logger.info('resolution: %s' % resolution)
        logger.info('fb100_resol: %s' % fb100)
        logger.info('self.pre_fb100: %s' % self.pre_fb100)
        logger.info('fb0_resol: %s' % fb0)
        logger.info('self.pre_fb0: %s' % self.pre_fb0)



        # for test
        # fb100 = price + 15
        # fb0 = price - 15

        # 최근 1시간을 본봉단위로 획득
        # fibo_l = self.input('length', int, 1440)  # 1Day = 60min * 24hr
        # fibo_l = self.input('length', int, 60)  # 1Day = 60min * 24hr
        # fibo100 = last(highest(high, fibo_l))
        # fibo0 = last(lowest(low, fibo_l))

        fb62 = math.ceil((fb100 - fb0) * 0.618 + fb0)
        fb38 = math.ceil((fb100 - fb0) * 0.382 + fb0)
        fb50 = math.ceil((fb100 - fb0) / 2 + fb0)

        fb200 = math.ceil((fb100 - fb0) * 1.0 + fb100)
        fb162 = math.ceil((fb100 - fb0) * 0.618 + fb100)
        fb138 = math.ceil((fb100 - fb0) * 0.382 + fb100)

        fb038 = math.ceil(fb0 - (fb100 - fb0) * 0.382)
        fb062 = math.ceil(fb0 - (fb100 - fb0) * 0.618)
        fb0100 = math.ceil(fb0 - (fb100 - fb0) * 1.00)

        qty= bitmex.get_position_size()

        # 익손평가
        longstatus = bitmex.get_position_avg_price() - fb0
        shortstatus = bitmex.get_position_avg_price() - fb100
        gprice = price
        if bitmex.get_whichpositon() == 'LONG' and longstatus > 0:
            qL0 = lot * 1
            qS100 = abs(qty) + lot * 1
            gprice = price - 1
        elif bitmex.get_whichpositon() == 'SHORT'and shortstatus > 0:
            qL0 = abs(qty) + lot * 1
            qS100 = lot * 1
            gprice = price + 1
        else:
            qL0 = lot * 1
            qS100 = lot * 1

        qS100 = lot*1
        qL0 = lot*1

        if self.pre_fb0 != 0 and fb0 != self.pre_fb0 and fb100 != self.pre_fb100:
            flg_changed_timezone = True
            logger.info('+++++++ flg_changed_timezone: %s' % flg_changed_timezone)

        if self.start == 1:
            # short position
            self.exchange.order("S200"+str(self.idx), False, lot*2, limit=fb200, post_only=True)
            self.exchange.order("S162"+str(self.idx), False, lot*1, limit=fb162, post_only=True)
            self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, post_only=True)
            self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, post_only=True)

            # long position
            self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, post_only=True)
            self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, post_only=True)
            self.exchange.order("L062"+str(self.idx), True, lot*1, limit=fb062, post_only=True)
            self.exchange.order("L0100"+str(self.idx), True, lot*2, limit=fb0100, post_only=True)


        L0 = bitmex.get_open_order("L0"+str(self.idx))
        L038 = bitmex.get_open_order("L038"+str(self.idx))
        L062 = bitmex.get_open_order("L062"+str(self.idx))
        L0100 = bitmex.get_open_order("L0100"+str(self.idx))

        S200 = bitmex.get_open_order("S200"+str(self.idx))
        S162 = bitmex.get_open_order("S162"+str(self.idx))
        S138 = bitmex.get_open_order("S138"+str(self.idx))
        S100 = bitmex.get_open_order("S100"+str(self.idx))

        #
        # logger.info('(L0 is None): %s' % (L0 is None))
        if flg_changed_timezone is True:
            self.idx += 1

            # 이전 self.idx-1 타임존의 기본 주문만 취소, 나머지 역지정 된것 들은 그냥 둔다.
            # self.exchange.cancel("L0"+str(self.idx-1))
            # self.exchange.cancel("L038"+str(self.idx-1))
            # self.exchange.cancel("L062"+str(self.idx-1))
            # self.exchange.cancel("L0100"+str(self.idx-1))
            # self.exchange.cancel("S200"+str(self.idx-1))
            # self.exchange.cancel("S162"+str(self.idx-1))
            # self.exchange.cancel("S138"+str(self.idx-1))
            # self.exchange.cancel("S100"+str(self.idx-1))
            self.exchange.cancel_all()
            longshort = True
            if bitmex.get_position_size() > 0:
                longshort = False
            if bitmex.get_position_size() < 0:
                longshort = True

            logger.info('bitmex.get_position_size(): %s' % bitmex.get_position_size())
            if bitmex.get_position_size() != 0:
                self.exchange.order("Garbage", longshort, bitmex.get_position_size(), limit=gprice, post_only=True)

            # self.exchange.cancel_all()
            # self.exchange.close_all()        # entry order
        # long position

        if price > fb0:
            logger.info('price > fb0:%')
            logger.info('flg_changed_timezone: %s' % flg_changed_timezone)
            self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, when=(L0 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, when=(L038 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("L062"+str(self.idx), True, lot*1, limit=fb062, when=(L062 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("L0100"+str(self.idx), True, lot*2, limit=fb0100, when=(L0100 is None or flg_changed_timezone), post_only=True)

        # short position
        if price < fb100:
            logger.info('price < fb100' )
            logger.info('flg_changed_timezone: %s' % flg_changed_timezone)

            self.exchange.order("S200"+str(self.idx), False, lot*2, limit=fb200, when=(S200 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("S162"+str(self.idx), False, lot*1, limit=fb162, when=(S162 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, when=(S138 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, when=(S100 is None or flg_changed_timezone), post_only=True)

        L0_w = bitmex.get_open_order("L0_w"+str(self.idx))
        L038_w = bitmex.get_open_order("L038_w"+str(self.idx))
        L062_w = bitmex.get_open_order("L062_w"+str(self.idx))
        L0100_w = bitmex.get_open_order("L0100_w"+str(self.idx))

        S100_w = bitmex.get_open_order("S100_w"+str(self.idx))
        S138_w = bitmex.get_open_order("S138_w"+str(self.idx))
        S162_w = bitmex.get_open_order("S162_w"+str(self.idx))
        S200_w = bitmex.get_open_order("S200_w"+str(self.idx))


        # win order of stoplimit
        if price <= fb0: #and L0 is None:
            self.exchange.order("L0_w"+str(self.idx), False, lot*1, limit=fb38, stop=fb0)  # post_only=True)
            logger.info('rice <= fb0: %s' % fb0)
        if price <= fb038: # and L038 is None:
            self.exchange.order("L038_w"+str(self.idx), False, lot*1, limit=fb0, stop=fb038)
            logger.info('price <= fb038: %s' % fb038)
        if price <= fb062: # and L062 is None:
            self.exchange.order("L062_w"+str(self.idx), False, lot*1, limit=fb038, stop=fb062)
            logger.info('price <= fb062: %s' % fb062)
        if price <= fb0100: # and L0100 is None:
            self.exchange.order("L0100_w"+str(self.idx), False, lot*2, limit=fb062, stop=fb0100)
            logger.info('price <= fb0100: %s' % fb0100)


        if price >= fb100: # and S100 is None:
            logger.info('price >= fb100: %s' % fb100)
            self.exchange.order("S100_w"+str(self.idx), True, lot*1, limit=fb62, stop=fb0100)
        if price >= fb138: # and S138 is None:
            self.exchange.order("S138_w"+str(self.idx), True, lot*1, limit=fb100, stop=fb138)
            logger.info('price >= fb138: %s' % fb138)
        if price >=fb162: # and S162 is None:
            self.exchange.order("S162_w"+str(self.idx), True, lot*1, limit=fb138, stop=fb162)
            logger.info('price >= fb162 %s' % fb162)
        if price >= fb200: # and S200 is None:
            self.exchange.order("S200_w"+str(self.idx), True, lot*2, limit=fb162, stop=fb200)
            logger.info('price >= fb200: %s' % fb200)

        # logger.info('bitmex.get_margin():%s' % bitmex.get_margin())
        # logger.info('bitmex.get_position():%s' % bitmex.get_position())

        self.pre_fb0 = fb0
        self.pre_fb100 = fb100

        # for debug
        logger.info('fb200: %s' % fb200)
        logger.info('fb162: %s' % fb162)
        logger.info('fb138: %s' % fb138)
        logger.info('fb100: %s' % fb100)
        logger.info('fb62: %s' % fb62)
        logger.info('fb50: %s' % fb50)
        logger.info('fb38: %s' % fb38)
        logger.info('fb0: %s' % fb0)
        logger.info('fb038: %s' % fb038)
        logger.info('fb062: %s' % fb062)
        logger.info('fb0100: %s' % fb0100)

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))

        realised_pnl = bitmex.get_margin()['realisedPnl']

        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)

        logger.info('--------------------------------------------------')


# rsi2
class RSI2(Bot): # logic https: // stock79.tistory.com / 177

    prebalance = BitMex(threading=False).get_balance()
    dealcount = 0
    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'length': hp.randint('length', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()

        # for test lot
        lot = int(round(lot / 50))
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        # variants settings
        rsi2_len = self.input('length', int, 2)
        rsi50_len = self.input('length', int, 50)
        rsi2 = rsi(close, rsi2_len)
        rsi50 = rsi(close, rsi50_len)

        factor = self.input('factor', int, 20)
        period = self.input('period', int, 7)

        resolution = self.input(defval=1, title="resolution", type=int) # defval 변경, 예) 5분 --> 5
        source = self.exchange.security(str(resolution) + 'm')  # def __init__  비교
        supertrenddf = supertrend(source, factor, period)

        fast_len = self.input('fast_len', int, 5)
        half_len = self.input('half_len', int, 5)
        slow_len = self.input('slow_len', int, 200)

        fast_sma = sma(close, fast_len)
        half_sma = sma(close, half_len)
        slow_sma = sma(close, slow_len)

        # conditions
        sma_long = over(fast_sma[-1], slow_sma[-1])
        sma_short = under(fast_sma[-1], slow_sma[-1])

        super_long = over(close[-1], supertrenddf['TSL'][-1])
        super_short = under(close[-1], supertrenddf['TSL'][-1])
        super_stoploss = supertrenddf['TSL'][-1]
        supertrendtrend = supertrenddf['Trend'][-1]

        rsi2_overbought = over(rsi2[-1], 95)
        rsi2_oversold = under(rsi2[-1], 5)

        rsi50_over = over(rsi50[-1], 50)
        rsi50_under = under(rsi50[-1], 50)

        price_under = under(price, half_sma[-1])
        price_over = over(price, half_sma[-1])

        half_before = over(close[-1], half_sma[-1])
        half_after = under(close[-1], half_sma[-1])

        # show infomations

        logger.info('price: %s' % price)

        logger.info('fast_sma[-1]: %s' % fast_sma[-1])
        logger.info('slow_sma[-1]: %s' % slow_sma[-1])


        logger.info('sma_long: %s' % sma_long)
        logger.info('sma_short: %s' % sma_short)

        logger.info('super_long: %s' % super_long)
        logger.info('super_short: %s' % super_short)
        logger.info('super_stoploss: %s' % super_stoploss)
        logger.info('sma_trend: %s' % supertrendtrend)

        logger.info('rsi2[-1 ]%s' % rsi2[-1])
        logger.info('rsi50[-1 ]%s' % rsi50[-1])
        logger.info('rsi2_oversold: %s' % rsi2_oversold)
        logger.info('rsi2_overbought: %s' % rsi2_overbought)

        logger.info('price_under: %s' % price_under)
        logger.info('price_over: %s' % price_over)

        logger.info('half_before: %s' % half_before)
        logger.info('half_after: %s' % half_after)

        logger.info('get_whichpositon(): %s' % bitmex.get_whichpositon())
        logger.info('position_size(): %s' % bitmex.get_position_size())


        # entry
        if super_long:  #long trend
            logger.info('+ + + + + LONG + + + + + LONG + + + + + LONG + + + + + ')
            if bitmex.get_whichpositon() is None:
                if sma_long and rsi2_oversold or price_under:
                    logger.info('postion condition > None > and all short condition order')
                    self.exchange.entry("Long", True, lot, limit=price-0.5, post_only=True)
                else:
                    logger.info('postion condition > None > default long order')
                    self.exchange.entry("Long", True, lot, limit=math.ceil(super_stoploss), post_only=True)
            elif bitmex.get_whichpositon() == 'LONG':
                logger.info('postion condition  > LONG')
                if price_over: # closing
                    logger.info('postion condition  > LONG > Closing')
                    self.exchange.order("Long", False, abs(bitmex.get_position_size()), limit=price + 1.5, post_only=True)
                elif rsi2_overbought: # add more entry
                    logger.info('postion condition  > LONG > Rsi2 overbougt add more entry')
                    self.exchange.entry("LongAdd", True, lot, limit=price - 0.5, post_only=True)
                elif super_short: # stop loss
                    logger.info('postion condition  > LONG > super_short(stop loss)')
                    self.exchange.entry("Long", True, lot)
                    self.exchange.entry("LongAdd", True, lot)

            elif bitmex.get_whichpositon() == 'SHORT':
                logger.info('cancel SHORT on long trend')
                # self.exchange.cancel_all()
                self.exchange.close_all()
            else:
                # self.exchange.cancel_all()
                logger.info('Super Long --> Else')

        if super_short:  # short trend
            logger.info('- - - - - SHORT - - - - - SHORT - - - - - SHORT - - - - - ')
            if bitmex.get_whichpositon() is None:
                if sma_short and rsi2_overbought or price_over:
                    logger.info('postion condition > None > and all short condition order')
                    self.exchange.entry("Short", False, lot, limit=price+0.5, post_only=True)
                else:
                    logger.info('postion condition > None > default short order')
                    self.exchange.entry("Short", False, lot, limit=math.floor(super_stoploss), post_only=True)
            elif bitmex.get_whichpositon() == 'SHORT':
                logger.info('postion condition  > SHORT')
                if price_under:  # closing
                    logger.info('postion condition  > SHORT > price_under(closing)')
                    self.exchange.order("Short", True, abs(bitmex.get_position_size()), limit=price - 1.5, post_only=True)
                elif rsi2_oversold:  # add more entry
                    logger.info('postion condition  > SHORT > rsi2_oversold(add more entry)')
                    self.exchange.entry("ShortAdd", False, lot, limit=price - 0.5, post_only=True)
                elif super_long:  # stop loss
                    logger.info('postion condition  > SHORT > super_short(stop loss)')
                    self.exchange.entry("Short", True, lot)
                    self.exchange.entry("ShortAdd", True, lot)

            elif bitmex.get_whichpositon() == 'LONG':
                logger.info('cancel LONG on short trend')
                self.exchange.close_all()
            else:

                logger.info('Super Shot --> Else')


        self.dealcount += 1

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))

        realised_pnl = bitmex.get_margin()['realisedPnl']

        logger.info('dealcount:%s' % self.dealcount)
        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)

        logger.info('--------------------------------------------------')


# OCC
class OCC(Bot):
    variants = [sma, ema, double_ema, triple_ema, wma, ssma, hull]
    eval_time = None

    def __init__(self):
        Bot.__init__(self, '1m')

    def ohlcv_len(self):
        return 15 * 30

    def options(self):
        return {
            'variant_type': hp.quniform('variant_type', 0, len(self.variants) - 1, 1),
            'basis_len': hp.quniform('basis_len', 1, 30, 1),
            'resolution': hp.quniform('resolution', 1, 10, 1),
            'sma_len': hp.quniform('sma_len', 1, 15, 1),
            'div_threshold': hp.quniform('div_threshold', 1, 6, 0.1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        variant_type = self.input(defval=5, title="variant_type", type=int)
        basis_len = self.input(defval=19,  title="basis_len", type=int)
        resolution = self.input(defval=2, title="resolution", type=int)
        sma_len = self.input(defval=9, title="sma_len", type=int)
        div_threshold = self.input(defval=3.0, title="div_threshold", type=float)

        source = self.exchange.security(str(resolution) + 'm')

        if self.eval_time is not None and \
                self.eval_time == source.iloc[-1].name:
            return

        series_open = source['open'].values
        series_close = source['close'].values

        variant = self.variants[variant_type]

        val_open = variant(series_open,  basis_len)
        val_close = variant(series_close, basis_len)

        if val_open[-1] > val_close[-1]:
            high_val = val_open[-1]
            low_val = val_close[-1]
        else:
            high_val = val_close[-1]
            low_val = val_open[-1]

        sma_val = sma(close, sma_len)

        self.exchange.plot('val_open', val_open[-1], 'b')
        self.exchange.plot('val_close', val_close[-1], 'r')
        logger.info("occ:sma_val[-1]:" + str(sma_val[-1]))
        logger.info("occ:low_val:" + str(low_val))
        logger.info("occ:high_val:" + str(high_val))
        logger.info("lot:" + str(lot))
        logger.info("------------")
        self.exchange.entry("Long", True,   lot, stop=math.floor(low_val), when=(sma_val[-1] < low_val))
        self.exchange.entry("Short", False, lot, stop=math.ceil(high_val), when=(sma_val[-1] > high_val))

        open_close_div = sma(numpy.abs(val_open - val_close), sma_len)

        if open_close_div[-1] > div_threshold and \
                open_close_div[-2] > div_threshold < open_close_div[-2]:
            self.exchange.close_all()

        self.eval_time = source.iloc[-1].name

# TradingView
class TV(Bot):
    subscriber = None

    def __init__(self):
        Bot.__init__(self, '1m')

        user_id = os.environ.get("GMAIL_ADDRESS")
        if user_id is None:
            raise Exception("Please set GMAIL_ADDRESS into env to use Trading View Strategy.")
        self.subscriber = GmailSub(user_id)
        self.subscriber.set_from_address('noreply@tradingview.com')

    def __on_message(self, messages):
        for message in messages:
            if 'payload' not in message:
                continue
            if 'headers' not in message['payload']:
                continue
            subject_list = [header['value']
                       for header in message['payload']['headers'] if header['name'] == 'Subject']
            if len(subject_list) == 0:
                continue
            subject = subject_list[0]
            if subject.startswith('TradingViewアラート:'):
                action = subject.replace('TradingViewアラート:', '')
                self.__action(action)

    def __action(self, action):
        lot = self.exchange.get_lot()
        if re.search('buy', action, re.IGNORECASE):
            self.exchange.entry('Long', True, lot)
        elif re.search('sell', action, re.IGNORECASE):
            self.exchange.entry('Short', True, lot)
        elif re.search('exit', action, re.IGNORECASE):
            self.exchange.close_all()

    def run(self):
        if self.hyperopt:
            raise Exception("Trading View Strategy dose not support hyperopt Mode.")
        elif self.back_test:
            raise Exception("Trading View Strategy dose not support backtest Mode.")
        elif self.stub_test:
            self.exchange = BitMexStub()
            logger.info(f"Bot Mode : Stub")
        else:
            self.exchange = BitMex(demo=self.test_net)
            logger.info(f"Bot Mode : Trade")

        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")
        logger.info(f"Resolution : {self.resolution()}")
        logger.info(f"Balance : {self.exchange.get_balance()}")

        notify(f"Starting Bot\n"
               f"Strategy : {type(self).__name__}\n"
               f"Resolution : {self.resolution()}\n"
               f"Balance : {self.exchange.get_balance()/100000000} XBT")

        self.subscriber.on_message(self.__on_message)

    def stop(self):
        self.subscriber.stop()

# サンプル戦略
class Sample(Bot):
    def __init__(self):
        # 第一引数: 戦略で使う足幅
        # 1分足で直近10期間の情報を戦略で必要とする場合
        Bot.__init__(self, '1m')

    def options(self):
        return {}

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, round(lot/1000))
            logger.info(f"Trade:Long")
        else:
            self.exchange.entry("Short", False, round(lot/1000))
            logger.info(f"Trade:Short")


class Cross(Bot):
    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'fast_len': hp.quniform('fast_len', 1, 30, 1),
            'slow_len': hp.quniform('slow_len', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        fast_len = self.input('fast_len', int, 9)
        slow_len = self.input('slow_len', int, 16)
        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)
        golden_cross = crossover(fast_sma, slow_sma)
        dead_cross = crossunder(fast_sma, slow_sma)

        if golden_cross:
            self.exchange.entry("Long", True, lot)
        if dead_cross:
            self.exchange.entry("Short", False, lot)



class Fibo2(Bot):
    prebalance = BitMex(threading=False).get_balance()
    start = 0
    pre_fb0 = 0
    pre_fb100 = 0
    idx = 0
    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
            'rcv_medium_len': hp.quniform('rcv_medium_len', 5, 15, 1),
            'rcv_long_len': hp.quniform('rcv_long_len', 10, 20, 1),
        }

    def strategy(self, open, close, high, low, volume):
        self.start += 1
        flg_changed_timezone = False

        lot = self.exchange.get_lot()
        # for test lot
        # lot = int(round(lot / 100))
        lot = 500
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()


        sma_base_l = self.input('sma_short_len', int, 200)

        resolution = self.input(defval=1, title="resolution", type=int) # defval 변경, 예) 5분 --> 5, 'm' or 1시간  1, 'h', 1Day 1, 'd'
        source = self.exchange.security(str(resolution) + 'h')  # def __init__  비교
        # logger.info('source: %s' % source)

        series_high = source['high'].values
        series_low = source['low'].values

        fb100 = last(highest(series_high, 1))  # 1시간 1, 1D의 경우는 resolution도 변경
        fb0 = last(lowest(series_low, 1))

        logger.info('resolution: %s' % resolution)
        logger.info('fb100_resol: %s' % fb100)
        logger.info('self.pre_fb100: %s' % self.pre_fb100)
        logger.info('fb0_resol: %s' % fb0)
        logger.info('self.pre_fb0: %s' % self.pre_fb0)



        # for test
        # fb100 = price + 15
        # fb0 = price - 15

        # 최근 1시간을 본봉단위로 획득
        # fibo_l = self.input('length', int, 1440)  # 1Day = 60min * 24hr
        # fibo_l = self.input('length', int, 60)  # 1Day = 60min * 24hr
        # fibo100 = last(highest(high, fibo_l))
        # fibo0 = last(lowest(low, fibo_l))

        fb62 = math.ceil((fb100 - fb0) * 0.618 + fb0)
        fb38 = math.ceil((fb100 - fb0) * 0.382 + fb0)
        fb50 = math.ceil((fb100 - fb0) / 2 + fb0)

        fb200 = math.ceil((fb100 - fb0) * 1.0 + fb100)
        fb162 = math.ceil((fb100 - fb0) * 0.618 + fb100)
        fb138 = math.ceil((fb100 - fb0) * 0.382 + fb100)

        fb038 = math.ceil(fb0 - (fb100 - fb0) * 0.382)
        fb062 = math.ceil(fb0 - (fb100 - fb0) * 0.618)
        fb0100 = math.ceil(fb0 - (fb100 - fb0) * 1.00)

        qty= bitmex.get_position_size()

        # 익손평가
        longstatus = bitmex.get_position_avg_price() - fb0
        shortstatus = bitmex.get_position_avg_price() - fb100

        if bitmex.get_whichpositon() == 'LONG' and longstatus > 0:
            qL0 = lot * 1
            qS100 = abs(qty) + lot * 1
        elif bitmex.get_whichpositon() == 'SHORT'and shortstatus > 0:
            qL0 = abs(qty) + lot * 1
            qS100 = lot * 1
        else:
            qL0 = lot * 1
            qS100 = lot * 1

        if fb0 != self.pre_fb0 and fb100 != self.pre_fb100 and self.pre_fb0 != 0:
            flg_changed_timezone = True
            logger.info('+++++++ flg_changed_timezone: %s' % flg_changed_timezone)

        if self.start == 1:
            # short position
            self.exchange.order("S200", False, lot*3, limit=fb200, post_only=True)
            self.exchange.order("S162", False, lot*2, limit=fb162, post_only=True)
            self.exchange.order("S138", False, lot*1, limit=fb138, post_only=True)
            self.exchange.order("S100", False, qS100, limit=fb100, post_only=True)

            # long position
            self.exchange.order("L0", True, qL0, limit=fb0, post_only=True)
            self.exchange.order("L038", True, lot*1, limit=fb038, post_only=True)
            self.exchange.order("L062", True, lot*2, limit=fb062, post_only=True)
            self.exchange.order("L0100", True, lot*3, limit=fb0100, post_only=True)


        L0 = bitmex.get_open_order("L0")
        L038 = bitmex.get_open_order("L038")
        L062 = bitmex.get_open_order("L062")
        L0100 = bitmex.get_open_order("L0100")

        S200 = bitmex.get_open_order("S200")
        S162 = bitmex.get_open_order("S162")
        S138 = bitmex.get_open_order("S138")
        S100 = bitmex.get_open_order("S100")

        #
        # logger.info('(L0 is None): %s' % (L0 is None))
        if flg_changed_timezone is True:
            self.idx += 1

        # entry order
        # long position
        if price > fb0:
            self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, when=(L0 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, when=(L038 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("L062"+str(self.idx), True, lot*2, limit=fb062, when=(L062 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("L0100"+str(self.idx), True, lot*3, limit=fb0100, when=(L0100 is None or flg_changed_timezone), post_only=True)

        # short position
        if price < fb100:
            self.exchange.order("S200"+str(self.idx), False, lot*3, limit=fb200, when=(S200 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("S162"+str(self.idx), False, lot*2, limit=fb162, when=(S162 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, when=(S138 is None or flg_changed_timezone), post_only=True)
            self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, when=(S100 is None or flg_changed_timezone), post_only=True)

        L0_w = bitmex.get_open_order("L0_w"+str(self.idx))
        L038_w = bitmex.get_open_order("L038_w"+str(self.idx))
        L062_w = bitmex.get_open_order("L062_w"+str(self.idx))
        L0100_w = bitmex.get_open_order("L0100_w"+str(self.idx))

        S100_w = bitmex.get_open_order("S100_w"+str(self.idx))
        S138_w = bitmex.get_open_order("S138_w"+str(self.idx))
        S162_w = bitmex.get_open_order("S162_w"+str(self.idx))
        S200_w = bitmex.get_open_order("S200_w"+str(self.idx))


        # win order of stoplimit
        if price < fb0 and L0 is None:
            self.exchange.order("L0_w"+str(self.idx), False, lot*1, limit=fb38, post_only=True)
            logger.info('rice <= fb0: %s' % fb0)
        if price < fb038 and L038 is None:
            self.exchange.order("L038_w"+str(self.idx), False, lot*1, limit=fb0, post_only=True)
            logger.info('price <= fb038: %s' % fb038)
        if price < fb062 and L062 is None:
            self.exchange.order("L062_w"+str(self.idx), False, lot*2, limit=fb038, post_only=True)
            logger.info('price <= fb062: %s' % fb062)
        if price < fb0100 and L0100 is None:
            # self.exchange.order("L0100_w"+str(self.idx), False, lot*3, limit=fb038, post_only=True)
            logger.info('rprice <= fb0100: %s' % fb0100)


        if price > fb100 and S100 is None:
            logger.info('price >= fb100: %s' % fb100)
            self.exchange.order("S100_w"+str(self.idx), True, lot*1, limit=fb62, post_only=True)
        if price > fb138 and S138 is None:
            self.exchange.order("S138_w"+str(self.idx), True, lot*1, limit=fb100, post_only=True)
            logger.info('price >= fb138: %s' % fb138)
        if price > fb162 and S162 is None:
            self.exchange.order("S162_w"+str(self.idx), True, lot*2, limit=fb138, post_only=True)
            logger.info('price >= fb162 %s' % fb162)
        if price > fb200 and S200 is None:
            self.exchange.order("S200_w"+str(self.idx), True, lot*3, limit=fb162, post_only=True)
            logger.info('price >= fb200: %s' % fb200)

        # logger.info('bitmex.get_margin():%s' % bitmex.get_margin())
        # logger.info('bitmex.get_position():%s' % bitmex.get_position())

        self.pre_fb0 = fb0
        self.pre_fb100 = fb100

        # for debug
        logger.info('fb200: %s' % fb200)
        logger.info('fb162: %s' % fb162)
        logger.info('fb138: %s' % fb138)
        logger.info('fb100: %s' % fb100)
        logger.info('fb62: %s' % fb62)
        logger.info('fb50: %s' % fb50)
        logger.info('fb38: %s' % fb38)
        logger.info('fb0: %s' % fb0)
        logger.info('fb038: %s' % fb038)
        logger.info('fb062: %s' % fb062)
        logger.info('fb0100: %s' % fb0100)

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))

        realised_pnl = bitmex.get_margin()['realisedPnl']

        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)

        logger.info('--------------------------------------------------')