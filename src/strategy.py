# coding: UTF-8
import os
import random
import math
import re
import numpy
import time
from hyperopt import hp
from src import highest, lowest, sma, crossover, crossunder, over, under, last, rci, rsi, double_ema, ema, triple_ema, wma, \
    ssma, hull, logger, notify, atr, willr, bbands, supertrend, heikinashi
from src.bitmex import BitMex
from src.bitmex_stub import BitMexStub
from src.bot import Bot
from src.gmail_sub import GmailSub
import pandas as pd

class Will_Rci(Bot):

    inlong = False
    inshort = False

    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 21, 1),
            'rcv_medium_len': hp.quniform('rcv_medium_len', 21, 34, 1),
            'rcv_long_len': hp.quniform('rcv_long_len', 34, 55, 1),
        }

    def strategy(self, open, close, high, low, volume):
        start = time.time()  # 시작 시간 저장
        lot = self.exchange.get_lot()

        itv_s = self.input('rcv_short_len', int, 21)
        itv_m = self.input('rcv_medium_len', int, 34)
        itv_l = self.input('rcv_long_len', int, 55)

        rci_s = rci(close, itv_s)
        rci_m = rci(close, itv_m)
        rci_l = rci(close, itv_l)

        ra = rci_s[-1] / 2 - 50
        rb = rci_m[-1] / 2 - 50
        rc = rci_l[-1] / 2 - 50

        # willr for five willilams
        a = willr(high, low, close, period=55)
        b = willr(high, low, close, period=144)
        c = willr(high, low, close, period=610)
        x = willr(high, low, close, period=4181)
        y = willr(high, low, close, period=6785)

        # logger.info('---- a ----')
        # for i in range(1, 5):
        #     logger.info('a [%s] *******: %s' % (-i, a[-i]))
        # logger.info('---- b ----')
        # for i in range(1, 5):
        #     logger.info('b [%s] *******: %s' % (-i, b[-i]))
        # logger.info('---- c ----')
        # for i in range(1, 5):
        #     logger.info('c [%s] *******: %s' % (-i, c[-i]))
        # logger.info('---- x ----')
        # for i in range(1, 5):
        #     logger.info('x [%s] *******: %s' % (-i, x[-i]))
        # logger.info('---- y ----')
        # for i in range(1, 5):
        #     logger.info('x [%s] *******: %s' % (-i, y[-i]))

        buycon1 = True if (a[-1] < -97 and (b[-1] < -97 or c[-1] < -97) and (x[-1] < -80 or y[-1] < -80)) else False
        buycon2 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -90) and (x[-1] > -35 or y[-1] > -35)) else False
        buycon3 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] > -70) and (x[-1] > -50 or y[-1] > -25)) else False
        buycon4 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -97) and (x[-1] > -50 or y[-1] > -50)) else False
        buycon5 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -75) and (x[-1] > -25 or y[-1] > -25)) else False
        buycon6 = True if ((b[-1] + 100) * (c[-1] + 100) == 0 and (c[-1] < -75 and x[-1] > -30 or y[-1] > -30)) else False
        buycon7 = True if ((b[-1] + 100) == 0 and (c[-1] > -30 and x[-1] > -30 or y[-1] > -30)) else False
        buycon8 = True if c[-1] < -97 else False
        buycon9 = True if a[-1] < -97 and b[-1] < -97 and c[-1] > -50 else False

        sellcon1 = True if (a[-1] > -3 and (b[-1] > -3 or c[-1] > -3) and (x[-1] > -20 or y[-1] > -20)) else False
        sellcon2 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] > -10) and (x[-1] < -65 or y[-1] < -65)) else False
        sellcon3 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] < -30) and (x[-1] < -50 or y[-1] < -75)) else False
        sellcon4 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] > -3) and (x[-1] < -50 or y[-1] < -50)) else False
        sellcon5 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] < -25) and (x[-1] < -75 or y[-1] < -75)) else False
        sellcon6 = True if (((b[-1]) * (c[-1])) == 0 and c[-1] > -25 and (x[-1] < -70 or y[-1] < -70)) else False
        sellcon7 = True if ((b[-1]) == 0 and (c[-1] < -70 and x[-1] < -70 or y[-1] < -70)) else False
        sellcon8 = True if c[-1] > -3 else False
        sellcon9 = True if a[-1] > -3 and b[-1] > -3 and c[-1] < -50 else False

        buyRCIfillerCon = True if rc < -80 else False
        sellRCIfillerCon = True if rc > -20 else False

        buyWillfilterCon = buycon1 or buycon2 or buycon3 or buycon4 or buycon5 or buycon6 or buycon7 or buycon8 or buycon9
        sellWillFilrerCon = sellcon1 or sellcon2 or sellcon3 or sellcon4 or sellcon5 or sellcon6 or sellcon7 or sellcon8 or sellcon9

        # set condition
        buyCons = buyWillfilterCon and buyRCIfillerCon
        sellCons = sellWillFilrerCon and sellRCIfillerCon

        buyCon = True if buyCons else False
        sellCon = True if sellCons else False


        # buyCloseCon = sellRCIfillerCon
        buyCloseCon = sellWillFilrerCon

        # sellCloseCon = buyRCIfillerCon
        sellCloseCon = buyWillfilterCon

        if buyCon:
            self.exchange.entry("Long", True, lot)
        if sellCon:
            self.exchange.entry("Short", False, lot)

        # if buyCon:
        #     self.exchange.entry("Long", True, lot)
        #     self.inlong = True
        # if buyCloseCon and self.inlong:
        #     self.exchange.close_all()
        #     self.inlong = False
        # if sellCon:
        #     self.exchange.entry("Short", False, lot)
        #     self.inshort = True
        # if sellCloseCon and self.inlong:
        #     self.exchange.close_all()
        #     self.inshort = False


# channel break out
class Doten(Bot):
    def __init__(self):
        Bot.__init__(self, '1m')

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


class YYY(Bot):
    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'fast_len': hp.quniform('fast_len', 1, 200, 1),
            'slow_len': hp.quniform('slow_len', 1, 600, 1),
        }

    def strategy(self, open, close, high, low, volume):

        lot = self.exchange.get_lot()
        # for test
        # lot = int(round(lot / 10))
        lot = 100
        logger.info('lot:%s' % lot)
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        fast_len = self.input('fast_len', int, 5)
        slow_len = self.input('slow_len', int, 18)
        trend_len = self.input('slow_len', int, 1200)
        logger.info('fast_len:%s' % fast_len)
        logger.info('slow_len:%s' % slow_len)

        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)
        trend_sma = sma(close, trend_len)
        uptrend = False
        downtrend = False
        if trend_sma[-1] > trend_sma[-3] or trend_sma[-1] > trend_sma[-10]:
            uptrend = True
        if trend_sma[-1] < trend_sma[-3] or trend_sma[-1] < trend_sma[-10]:
            downtrend = True

        golden_cross = crossover(fast_sma, slow_sma)
        dead_cross = crossunder(fast_sma, slow_sma)

        logger.info('golden_cross:%s' % golden_cross)
        logger.info('dead_cross:%s' % dead_cross)
        logger.info('price:%s' % price)
        logger.info('trend_sma:%s' % trend_sma[-1])
        logger.info('uptrend : %s' % str(uptrend))
        logger.info('downtrend : %s' % str(downtrend))

        # long
        if dead_cross and uptrend:
            self.exchange.order("Long", True, lot, limit=price-0.5, when=True, post_only=True)
            logger.info('in dead_cross and uptrend for long')

        if bitmex.get_whichpositon() == 'LONG':
            self.exchange.order("Long", False, lot, limit=price + 0.5, when=golden_cross, post_only=True)  # similar stop function

        # short
        if golden_cross and downtrend:
            logger.info('in golden_cross and uptrend for short')
            self.exchange.entry("Short", False, lot, limit=price+0.5, when=True, post_only=True)
        if bitmex.get_whichpositon() == 'SHORT':
            self.exchange.order("Short", True, lot, limit=price-0.5, stop=(price-0.5), when=dead_cross, post_only=True)

        logger.info('--------------------------------------------------')

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


# william R and rci
class Willr(Bot):
    prebalance = BitMex(threading=False).get_balance()
    start = 0
    pre_fb0 = 0
    pre_fb100 = 0
    inlong = False
    inshort = False
    firstlong = False
    firstshort = False

    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 21, 1),
            'rcv_medium_len': hp.quniform('rcv_medium_len', 21, 34, 1),
            'rcv_long_len': hp.quniform('rcv_long_len', 34, 55, 1),
        }

    def strategy(self, open, close, high, low, volume):
        start = time.time()  # 시작 시간 저장

        self.start += 1
        flg_changed_timezone = False
        # lot = self.exchange.get_lot()
        # for test lot
        # lot = int(round(lot / 20))
        lot = 100
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        itv_s = self.input('rcv_short_len', int, 21)
        itv_m = self.input('rcv_medium_len', int, 34)
        itv_l = self.input('rcv_long_len', int, 55)

        rci_s = rci(close, itv_s)
        rci_m = rci(close, itv_m)
        rci_l = rci(close, itv_l)

        ra = rci_s[-1] / 2 - 50
        rb = rci_m[-1] / 2 - 50
        rc = rci_l[-1] / 2 - 50

        # willr for five willilams
        a = willr(high, low, close, period=55)
        b = willr(high, low, close, period=144)
        c = willr(high, low, close, period=610)
        x = willr(high, low, close, period=4181)
        y = willr(high, low, close, period=6785)

        # logger.info('---- a ----')
        # for i in range(1, 5):
        #     logger.info('a [%s] *******: %s' % (-i, a[-i]))
        # logger.info('---- b ----')
        # for i in range(1, 5):
        #     logger.info('b [%s] *******: %s' % (-i, b[-i]))
        # logger.info('---- c ----')
        # for i in range(1, 5):
        #     logger.info('c [%s] *******: %s' % (-i, c[-i]))
        # logger.info('---- x ----')
        # for i in range(1, 5):
        #     logger.info('x [%s] *******: %s' % (-i, x[-i]))
        # logger.info('---- y ----')
        # for i in range(1, 5):
        #     logger.info('x [%s] *******: %s' % (-i, y[-i]))

        logger.info('-----------------price / lot ----------------')
        logger.info('price:%s' % price)
        logger.info('lot:%s' % str(lot))
        logger.info('-----------------o h l c v ----------------')
        logger.info('open:%s' % open[-1])
        logger.info('high:%s' % high[-1])
        logger.info('low:%s' % low[-1])
        logger.info('close:%s' % close[-1])
        logger.info('volume:%s' % volume[-1])
        logger.info('-----------------a b c x y ----------------')
        logger.info('willr_a : %s' % a[-1])
        logger.info('willr_b : %s' % b[-1])
        logger.info('willr_c : %s' % c[-1])
        logger.info('willr_x : %s' % x[-1])
        logger.info('willr_y : %s' % y[-1])
        logger.info('willr_rc : %s' % rc)


        buycon1 = True if (a[-1] < -97 and (b[-1] < -97 or c[-1] < -97) and (x[-1] < -80 or y[-1] < -80)) else False
        buycon2 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -90) and (x[-1] > -35 or y[-1] > -35)) else False
        buycon3 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] > -70) and (x[-1] > -50 or y[-1] > -25)) else False
        buycon4 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -97) and (x[-1] > -50 or y[-1] > -50)) else False
        buycon5 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -75) and (x[-1] > -25 or y[-1] > -25)) else False
        buycon6 = True if ((b[-1] + 100) * (c[-1] + 100) == 0 and (c[-1] < -75 and x[-1] > -30 or y[-1] > -30)) else False
        buycon7 = True if ((b[-1] + 100) == 0 and (c[-1] > -30 and x[-1] > -30 or y[-1] > -30)) else False
        buycon8 = True if c[-1] < -97 else False
        buycon9 = True if a[-1] < -97 and b[-1] < -97 and c[-1] > -50 else False

        sellcon1 = True if (a[-1] > -3 and (b[-1] > -3 or c[-1] > -3) and (x[-1] > -20 or y[-1] > -20)) else False
        sellcon2 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] > -10) and (x[-1] < -65 or y[-1] < -65)) else False
        sellcon3 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] < -30) and (x[-1] < -50 or y[-1] < -75)) else False
        sellcon4 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] > -3) and (x[-1] < -50 or y[-1] < -50)) else False
        sellcon5 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] < -25) and (x[-1] < -75 or y[-1] < -75)) else False
        sellcon6 = True if (((b[-1]) * (c[-1])) == 0 and c[-1] > -25 and (x[-1] < -70 or y[-1] < -70)) else False
        sellcon7 = True if ((b[-1]) == 0 and (c[-1] < -70 and x[-1] < -70 or y[-1] < -70)) else False
        sellcon8 = True if c[-1] > -3 else False
        sellcon9 = True if a[-1] > -3 and b[-1] > -3 and c[-1] < -50 else False

        # buyCloseCon = True if a[-1] > -10 else False
        # sellCloseCon = True if a[-1] < -90 else False
        buyRCIfillerCon = True if rc < -80 else False
        sellRCIfillerCon = True if rc > -20 else False

        buyWillfilterCon = buycon1 or buycon2 or buycon3 or buycon4 or buycon5 or buycon6 or buycon7 or buycon8 or buycon9
        sellWillFilrerCon = sellcon1 or sellcon2 or sellcon3 or sellcon4 or sellcon5 or sellcon6 or sellcon7 or sellcon8 or sellcon9

        # set condition
        buyCons = buyWillfilterCon and buyRCIfillerCon
        sellCons = sellWillFilrerCon and sellRCIfillerCon

        buyCon = True if buyCons else False
        sellCon = True if sellCons else False

        # buyCloseCon = sellRCIfillerCon
        buyCloseCon = sellWillFilrerCon

        # sellCloseCon = buyRCIfillerCon
        sellCloseCon = buyWillfilterCon

        logger.info('-----------------inlong / inshort ----------------')
        logger.info('inlong:%s' % self.inlong)
        logger.info('inshort:%s' % self.inshort)
        logger.info('-----------------buyCon / sellCon ----------------')
        logger.info('buyCon:%s' % buyCon)
        logger.info('sellCon:%s' % sellCon)

        logger.info('buyCloseCon:%s' % buyCloseCon)
        logger.info('sellCloseCon:%s' % sellCloseCon)

        logger.info('bitmex.get_whichpositon():%s' % bitmex.get_whichpositon())
        logger.info('bitmex.get_position_size():%s' % bitmex.get_position_size())


        if bitmex.get_position_size() > 0:
            logger.info('-- >> bitmex.get_position_size > 0 --')
            self.inlong = True
        elif bitmex.get_position_size() < 0:
            logger.info('-- >> bitmex.get_position_size < 0 --')
            self.inshort = True

        if self.start==1:
            logger.info('-- self.start==1 --')
            self.exchange.cancel_all()

        elif (flg_changed_timezone):
            logger.info('-- (flg_changed_timezone')
            self.exchange.cancel_all()

            # init
            if bitmex.get_whichpositon() is None and (self.inlong is True or self.inshort is True):
                logger.info('-- (flg_changed_timezone >> init: inlone --> %s, inshort --> %s' % (self.inlong, self.inshort))
                self.inlong = False
                self.inshort = False

        else:
            logger.info('-- else and pass --')
            pass

        if (buyCloseCon) and (self.inlong):
            # self.exchange.close("Long")
            logger.info('-- (buyCloseCon) and (self.inlong) --')
            self.exchange.close_all()
            self.inlong = False

        if (sellCloseCon) and (self.inshort):
            # self.exchange.close("Short")
            logger.info('-- (sellCloseCon) and (self.inshort) --')
            self.exchange.close_all()
            self.inshort = False

        if (buyCon) and (not self.inlong):
            logger.info('if (buyCon) and (not self.inlong)::')
            if price <= close[-1]:
                logger.info('>> in +++ price <= close[-1] and ++++ get_position_size: %s' % bitmex.get_position_size())
                if bitmex.get_position_size() !=  0:
                    logger.info('-- bitmex.get_position_size() != 0 --')
                    self.exchange.order("Long", True, bitmex.get_position_size()*2, limit=price-0.5, post_only=True)
                else:
                    logger.info('-- bitmex.get_position_size() != 0 / else --')
                    self.exchange.order("Long", True, lot, limit=price-0.5, post_only=True)
            elif price < low[-1]:
                logger.info('-- price < low[-1] --')
                self.exchange.order("Long", True, lot, limit=price-0.5, post_only=True)
            else:
                pass

        if (sellCon) and (not self.inshort):
            logger.info('if (sellCon) and (not self.inlong)::')
            if price >= close[-1]:
                logger.info('>> in +++ price >= close[-1] and ++++ get_position_size: %s' % bitmex.get_position_size())
                if bitmex.get_position_size() != 0:
                    logger.info('-- bitmex.get_position_size() !=  0 --')
                    self.exchange.order("Short", False, bitmex.get_position_size()*2, limit=price+0.5, post_only=True)
                else:
                    logger.info('-- bitmex.get_position_size() != 0 / else --')
                    self.exchange.order("Short", False, lot, limit=price+0.5, post_only=True)
            elif price > high[-1]:
                logger.info('-- price > high[-1] --')
                self.exchange.order("Long", False, lot, limit=price+0.5, post_only=True)
            else:
                pass

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))
        realised_pnl = bitmex.get_margin()['realisedPnl']
        logger.info('----------------- realised_pnl ---------')
        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)
        logger.info("time2 : %s" % str(time.time() - start))
        logger.info('----------------- END ---------------- END ----------------')

# william R and Fibo
class WillnFibo(Bot):
    prebalance = BitMex(threading=False).get_balance()
    start = 0
    pre_fb0 = 0
    pre_fb100 = 0
    inlong = False
    inshort = False
    firstlong = False
    firstshort = False

    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
            'rcv_medium_len': hp.quniform('rcv_medium_len', 5, 15, 1),
            'rcv_long_len': hp.quniform('rcv_long_len', 10, 20, 1),
        }

    def strategy(self, open, close, high, low, volume):
        start = time.time()  # 시작 시간 저장

        self.start += 1
        flg_changed_timezone = False
        # lot = self.exchange.get_lot()
        # # for test lot
        # # lot = int(round(lot / 20))
        lot = 100
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        # channel breakout for 1D
        resolution_d = self.input(defval=1, title="resolution", type=int)
        source_d = self.exchange.security(str(resolution_d) + 'd')
        series_high_d = source_d['high'].values
        series_low_d = source_d['low'].values
        up = last(highest(series_high_d, 1))
        dn = last(lowest(series_low_d, 1))
        logger.info("time1 :%s" % str(time.time() - start))
        start = time.time()  # 시작 시간 저장

        # self.exchange.entry("ChLong", True, round(lot), stop=up)
        # self.exchange.entry("ChShort", False, round(lot), stop=dn)

        # fibo for 1h
        resolution = self.input(defval=1, title="resolution", type=int)
        source = self.exchange.security(str(resolution) + 'h')
        series_high = source['high'].values
        series_low = source['low'].values

        fb100 = last(highest(series_high, 1))  # 1시간 1, 1D의 경우는 resolution도 변경
        fb0 = last(lowest(series_low, 1))

        logger.info('resolution: %s' % resolution)
        logger.info('fb100_resol: %s' % fb100)
        logger.info('fb0_resol: %s' % fb0)
        logger.info('self.pre_fb100: %s' % self.pre_fb100)
        logger.info('self.pre_fb0: %s' % self.pre_fb0)

        if self.pre_fb0 != 0 and fb0 != self.pre_fb0 and fb100 != self.pre_fb100:
            flg_changed_timezone = True
            logger.info('+++++++ flg_changed_timezone: %s' % flg_changed_timezone)
            if bitmex.get_whichpositon() is None:
                self.exchange.cancel_all()

        fb62 = math.ceil((fb100 - fb0) * 0.618 + fb0)
        fb38 = math.ceil((fb100 - fb0) * 0.382 + fb0)
        fb50 = math.ceil((fb100 - fb0) / 2 + fb0)

        fb200 = math.ceil((fb100 - fb0) * 1.0 + fb100)
        fb162 = math.ceil((fb100 - fb0) * 0.618 + fb100)
        fb138 = math.ceil((fb100 - fb0) * 0.382 + fb100)

        fb038 = math.ceil(fb0 - (fb100 - fb0) * 0.382)
        fb062 = math.ceil(fb0 - (fb100 - fb0) * 0.618)
        fb0100 = math.ceil(fb0 - (fb100 - fb0) * 1.00)

        # willr for five willilams
        a = willr(high, low, close, period=55)
        b = willr(high, low, close, period=144)
        c = willr(high, low, close, period=610)
        x = willr(high, low, close, period=4181)
        y = willr(high, low, close, period=6785)

        # logger.info('---- a ----')
        # for i in range(1, 5):
        #     logger.info('a [%s] *******: %s' % (-i, a[-i]))
        # logger.info('---- b ----')
        # for i in range(1, 5):
        #     logger.info('b [%s] *******: %s' % (-i, b[-i]))
        # logger.info('---- c ----')
        # for i in range(1, 5):
        #     logger.info('c [%s] *******: %s' % (-i, c[-i]))
        # logger.info('---- x ----')
        # for i in range(1, 5):
        #     logger.info('x [%s] *******: %s' % (-i, x[-i]))
        # logger.info('---- y ----')
        # for i in range(1, 5):
        #     logger.info('x [%s] *******: %s' % (-i, y[-i]))

        logger.info('-----------------price / lot ----------------')
        logger.info('price:%s' % price)
        logger.info('lot:%s' % str(lot))
        logger.info('-----------------o h l c v ----------------')
        logger.info('open:%s' % open[-1])
        logger.info('high:%s' % high[-1])
        logger.info('low:%s' % low[-1])
        logger.info('close:%s' % close[-1])
        logger.info('volume:%s' % volume[-1])
        logger.info('-----------------a b c x y ----------------')
        logger.info('willr_a : %s' % a[-1])
        logger.info('willr_b : %s' % b[-1])
        logger.info('willr_c : %s' % c[-1])
        logger.info('willr_x : %s' % x[-1])
        logger.info('willr_y : %s' % y[-1])


        buycon1 = True if (a[-1] < -97 and (b[-1] < -97 or c[-1] < -97) and (x[-1] < -80 or y[-1] < -80)) else False
        buycon2 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -90) and (x[-1] > -35 or y[-1] > -35)) else False
        buycon3 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] > -70) and (x[-1] > -50 or y[-1] > -25)) else False
        buycon4 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -97) and (x[-1] > -50 or y[-1] > -50)) else False
        buycon5 = True if (a[-1] < -97 and (b[-1] < -97 and c[-1] < -75) and (x[-1] > -25 or y[-1] > -25)) else False
        buycon6 = True if ((b[-1] + 100) * (c[-1] + 100) == 0 and (c[-1] < -75 and x[-1] > -30 or y[-1] > -30)) else False
        buycon7 = True if ((b[-1] + 100) == 0 and (c[-1] > -30 and x[-1] > -30 or y[-1] > -30)) else False
        buycon8 = True if c[-1] < -97 else False
        buycon9 = True if a[-1] < -97 and b[-1] < -97 and c[-1] > -50 else False

        sellcon1 = True if (a[-1] > -3 and (b[-1] > -3 or c[-1] > -3) and (x[-1] > -20 or y[-1] > -20)) else False
        sellcon2 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] > -10) and (x[-1] < -65 or y[-1] < -65)) else False
        sellcon3 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] < -30) and (x[-1] < -50 or y[-1] < -75)) else False
        sellcon4 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] > -3) and (x[-1] < -50 or y[-1] < -50)) else False
        sellcon5 = True if (a[-1] > -3 and (b[-1] > -3 and c[-1] < -25) and (x[-1] < -75 or y[-1] < -75)) else False
        sellcon6 = True if (((b[-1]) * (c[-1])) == 0 and c[-1] > -25 and (x[-1] < -70 or y[-1] < -70)) else False
        sellcon7 = True if ((b[-1]) == 0 and (c[-1] < -70 and x[-1] < -70 or y[-1] < -70)) else False
        sellcon8 = True if c[-1] > -3 else False
        sellcon9 = True if a[-1] > -3 and b[-1] > -3 and c[-1] < -50 else False

        buyCon = True if buycon1 or buycon2 or buycon3 or buycon4 or buycon5 or buycon6 or buycon7 or buycon8 or buycon9 else False
        sellCon = True if sellcon1 or sellcon2 or sellcon3 or sellcon4 or sellcon5 or sellcon6 or sellcon7 or sellcon8 or sellcon9 else False

        buyCloseCon = True if a[-1] > -10 else False
        sellCloseCon = True if a[-1] < -90 else False

        logger.info('-----------------inlong / inshort ----------------')
        logger.info('inlong:%s' % self.inlong)
        logger.info('inshort:%s' % self.inshort)
        logger.info('-----------------buyCon / sellCon ----------------')
        logger.info('buyCon:%s' % buyCon)
        logger.info('sellCon:%s' % sellCon)

        logger.info('buyCloseCon:%s' % buyCloseCon)
        logger.info('sellCloseCon:%s' % sellCloseCon)


        # if self.inlong:
        #     self.inlong = True
        #
        # if self.inshort:
        #     self.inshort = True

        fb100_4h = last(highest(series_high, 4))  # 1시간 1, 1D의 경우는 resolution도 변경
        fb0_4h = last(lowest(series_low, 4))

        fiboBuyCon = True if fb0 <= fb0_4h else False
        logger.info('fiboBuyCon:%s' % fiboBuyCon)

        fiboSellCon = True if fb100 >= fb100_4h else False
        logger.info('fiboSellCon:%s' % fiboSellCon)

        logger.info('bitmex.get_whichpositon():%s' % bitmex.get_whichpositon())
        logger.info('bitmex.get_position_size():%s' % bitmex.get_position_size())

        # if bitmex.get_whichpositon() is not None:
        #     logger.info('-- bitmex.get_whichpositon is not None --')
        if bitmex.get_position_size() > 0:
            logger.info('-- >> bitmex.get_position_size > 0 --')
            self.inlong = True
        elif bitmex.get_position_size() < 0:
            logger.info('-- >> bitmex.get_position_size < 0 --')
            self.inshort = True

        if self.start==1:
            logger.info('-- self.start==1 --')
            self.exchange.cancel_all()
            if fiboBuyCon:
                logger.info('if fiboBuyCon:%s' % fiboBuyCon)
                self.exchange.order("FLong", True, lot, limit=fb062, post_only=True)
            if fiboSellCon:
                logger.info('if fiboSellCon:%s' % fiboSellCon)
                self.exchange.order("FShort", False, lot, limit=fb162, post_only=True)
            if price < up:
                logger.info('price < up: %s' % up)
                self.exchange.order("ChLong", True, lot, stop=up)
            if price > dn:
                logger.info('price > dn: %s' % dn)
                self.exchange.order("ChShort", False, lot, stop=dn)

        elif (flg_changed_timezone):  # and (not self.inlong)) and (not self.inshort):
            logger.info('-- (flg_changed_timezone') #and (not self.inlong)) and (not self.inshort) --')
            self.exchange.cancel_all()

            # init
            if bitmex.get_whichpositon() is None and (self.inlong is True or self.inshort is True):
                logger.info('-- (flg_changed_timezone >> init: inlone --> %s, inshort --> %s' % (self.inlong, self.inshort))
                self.inlong = False
                self.inshort = False

            # set fibo conditions
            if fiboBuyCon:
                logger.info('if fiboBuyCon:%s' % fiboBuyCon)
                self.exchange.order("FLong", True, lot, limit=fb062, post_only=True)
            if fiboSellCon:
                logger.info('if fiboSellCon:%s' % fiboSellCon)
                self.exchange.order("FShort", False, lot, limit=fb162, post_only=True)

            if price < up:
                logger.info('price < up: %s' % up)
                self.exchange.order("ChLong", True, lot, stop=up)
            if price > dn:
                logger.info('price > dn: %s' % dn)
                self.exchange.order("ChShort", False, lot, stop=dn)

        # elif (flg_changed_timezone and self.inlong and not self.inshort):
        #     logger.info('-- (flg_changed_timezone and self.inlong and not self.inshort) --')
        #     self.exchange.order("FShort", False, lot, limit=fb200, post_only=True)
        # elif (flg_changed_timezone and not self.inlong and self.inshort):
        #     logger.info('-- (flg_changed_timezone and not self.inlong and self.inshort) --')
        #     self.exchange.order("FLong", True, lot, limit=fb0100, post_only=True)
        else:
            logger.info('-- else and pass --')
            pass

        if (buyCloseCon) and (self.inlong):
            # self.exchange.close("Long")
            logger.info('-- (buyCloseCon) and (self.inlong) --')
            self.exchange.close_all()
            self.inlong = False

        if (sellCloseCon) and (self.inshort):
            # self.exchange.close("Short")
            logger.info('-- (sellCloseCon) and (self.inshort) --')
            self.exchange.close_all()
            self.inshort = False

        if (buyCon) and (not self.inlong):
            logger.info('if (buyCon) and (not self.inlong)::')
            if price <= close[-1]:
                logger.info('>> in +++ price <= close[-1] and ++++ get_position_size: %s' % bitmex.get_position_size())
                if bitmex.get_position_size() !=  0:
                    logger.info('-- bitmex.get_position_size() != 0 --')
                    self.exchange.order("Long", True, bitmex.get_position_size()*2, limit=price-0.5, post_only=True)
                else:
                    logger.info('-- bitmex.get_position_size() != 0 / else --')
                    self.exchange.order("Long", True, lot, limit=price-0.5, post_only=True)
                # self.inlong = True
            else:
                pass

        if (sellCon) and (not self.inshort):
            logger.info('if (sellCon) and (not self.inlong)::')
            if price >= close[-1]:
                logger.info('>> in +++ price >= close[-1] and ++++ get_position_size: %s' % bitmex.get_position_size())
                if bitmex.get_position_size() != 0:
                    logger.info('-- bitmex.get_position_size() !=  0 --')
                    self.exchange.order("Short", False, bitmex.get_position_size()*2, limit=price+0.5, post_only=True)
                else:
                    logger.info('-- bitmex.get_position_size() != 0 / else --')
                    self.exchange.order("Short", False, lot, limit=price+0.5, post_only=True)
                # self.inshort = True
            else:
                pass

        # save pre-timezone's fb0, fb100 values
        self.pre_fb0 = fb0
        self.pre_fb100 = fb100

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))
        realised_pnl = bitmex.get_margin()['realisedPnl']
        logger.info('----------------- realised_pnl ---------')
        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)
        logger.info("time2 : %s" % str(time.time() - start))
        logger.info('----------------- END ---------------- END ----------------')
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
# class Fibo(Bot):
#     prebalance = BitMex(threading=False).get_balance()
#     start = 0
#     pre_fb0 = 0
#     pre_fb100 = 0
#     idx = 0
#     def __init__(self):
#         Bot.__init__(self, '1m')
#
#     def options(self):
#         return {
#             'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
#         }
#
#     def strategy(self, open, close, high, low, volume):
#         self.start += 1
#         flg_changed_timezone = False
#
#         lot = self.exchange.get_lot()
#         # for test lot
#         # lot = int(round(lot / 20))
#         lot = 500
#         bitmex = BitMex(threading=False)
#         price = bitmex.get_market_price()
#
#
#         sma_base_l = self.input('sma_short_len', int, 200)
#
#         resolution = self.input(defval=5, title="resolution", type=int) # defval 변경, 예) 5분 --> 5, 'm' or 1시간  1, 'h', 1Day 1, 'd'
#         source = self.exchange.security(str(resolution) + 'm')  # def __init__  비교
#         logger.info('source: %s' % source)
#
#         series_high = source['high'].values
#         series_low = source['low'].values
#
#         fb100 = last(highest(series_high, 1))  # 1시간 1, 1D의 경우는 resolution도 변경
#         fb0 = last(lowest(series_low, 1))
#
#         logger.info('resolution: %s' % resolution)
#         logger.info('fb100_resol: %s' % fb100)
#         logger.info('self.pre_fb100: %s' % self.pre_fb100)
#         logger.info('fb0_resol: %s' % fb0)
#         logger.info('self.pre_fb0: %s' % self.pre_fb0)
#
#
#
#         # for test
#         # fb100 = price + 15
#         # fb0 = price - 15
#
#         # 최근 1시간을 본봉단위로 획득
#         # fibo_l = self.input('length', int, 1440)  # 1Day = 60min * 24hr
#         # fibo_l = self.input('length', int, 60)  # 1Day = 60min * 24hr
#         # fibo100 = last(highest(high, fibo_l))
#         # fibo0 = last(lowest(low, fibo_l))
#
#         fb62 = math.ceil((fb100 - fb0) * 0.618 + fb0)
#         fb38 = math.ceil((fb100 - fb0) * 0.382 + fb0)
#         fb50 = math.ceil((fb100 - fb0) / 2 + fb0)
#
#         fb200 = math.ceil((fb100 - fb0) * 1.0 + fb100)
#         fb162 = math.ceil((fb100 - fb0) * 0.618 + fb100)
#         fb138 = math.ceil((fb100 - fb0) * 0.382 + fb100)
#
#         fb038 = math.ceil(fb0 - (fb100 - fb0) * 0.382)
#         fb062 = math.ceil(fb0 - (fb100 - fb0) * 0.618)
#         fb0100 = math.ceil(fb0 - (fb100 - fb0) * 1.00)
#
#         qty= bitmex.get_position_size()
#
#         # 익손평가
#         longstatus = bitmex.get_position_avg_price() - fb0
#         shortstatus = bitmex.get_position_avg_price() - fb100
#         gprice = price
#
#         # if bitmex.get_whichpositon() == 'LONG' and longstatus > 0:
#         #     qL0 = lot * 1
#         #     qS100 = abs(qty) + lot * 1
#         #     gprice = price - 1
#         # elif bitmex.get_whichpositon() == 'SHORT'and shortstatus > 0:
#         #     qL0 = abs(qty) + lot * 1
#         #     qS100 = lot * 1
#         #     gprice = price + 1
#         # else:
#         #     qL0 = lot * 1
#         #     qS100 = lot * 1
#
#         qS100 = lot*1
#         qL0 = lot*1
#
#         if self.pre_fb0 != 0 and fb0 != self.pre_fb0 and fb100 != self.pre_fb100:
#             flg_changed_timezone = True
#             logger.info('+++++++ flg_changed_timezone: %s' % flg_changed_timezone)
#             if bitmex.get_whichpositon() is None:
#                 self.exchange.cancel_all()
#
#
#         if self.start == 1:
#             # short position
#             self.exchange.order("S200"+str(self.idx), False, lot*2, limit=fb200, post_only=True)
#             # self.exchange.order("S162"+str(self.idx), False, lot*1, limit=fb162, post_only=True)
#             self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, post_only=True)
#             self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, post_only=True)
#
#             # long position
#             self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, post_only=True)
#             self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, post_only=True)
#             # self.exchange.order("L062"+str(self.idx), True, lot*1, limit=fb062, post_only=True)
#             self.exchange.order("L0100"+str(self.idx), True, lot*2, limit=fb0100, post_only=True)
#
#
#         L0 = bitmex.get_open_order("L0"+str(self.idx))
#         L038 = bitmex.get_open_order("L038"+str(self.idx))
#         L062 = bitmex.get_open_order("L062"+str(self.idx))
#         L0100 = bitmex.get_open_order("L0100"+str(self.idx))
#
#         S200 = bitmex.get_open_order("S200"+str(self.idx))
#         S162 = bitmex.get_open_order("S162"+str(self.idx))
#         S138 = bitmex.get_open_order("S138"+str(self.idx))
#         S100 = bitmex.get_open_order("S100"+str(self.idx))
#
#         #
#         # logger.info('(L0 is None): %s' % (L0 is None))
#         if flg_changed_timezone is True:
#             self.idx += 1
#
#             # 이전 self.idx-1 타임존의 기본 주문만 취소, 나머지 역지정 된것 들은 그냥 둔다.
#             # self.exchange.cancel("L0"+str(self.idx-1))
#             # self.exchange.cancel("L038"+str(self.idx-1))
#             # self.exchange.cancel("L062"+str(self.idx-1))
#             # self.exchange.cancel("L0100"+str(self.idx-1))
#             # self.exchange.cancel("S200"+str(self.idx-1))
#             # self.exchange.cancel("S162"+str(self.idx-1))
#             # self.exchange.cancel("S138"+str(self.idx-1))
#             # self.exchange.cancel("S100"+str(self.idx-1))
#             self.exchange.cancel_all()
#             longshort = True
#             if bitmex.get_position_size() > 0:
#                 longshort = False
#             if bitmex.get_position_size() < 0:
#                 longshort = True
#
#             logger.info('bitmex.get_position_size(): %s' % bitmex.get_position_size())
#             if bitmex.get_position_size() != 0:
#                 self.exchange.order("Garbage", longshort, bitmex.get_position_size(), limit=gprice, post_only=True)
#
#             # self.exchange.cancel_all()
#             # self.exchange.close_all()        # entry order
#         # long position
#
#         if price > fb0:
#             logger.info('price > fb0:%')
#             logger.info('flg_changed_timezone: %s' % flg_changed_timezone)
#             self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, when=(L0 is None or flg_changed_timezone), post_only=True)
#             self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, when=(L038 is None or flg_changed_timezone), post_only=True)
#             # self.exchange.order("L062"+str(self.idx), True, lot*1, limit=fb062, when=(L062 is None or flg_changed_timezone), post_only=True)
#             self.exchange.order("L0100"+str(self.idx), True, lot*2, limit=fb0100, when=(L0100 is None or flg_changed_timezone), post_only=True)
#
#         # short position
#         if price < fb100:
#             logger.info('price < fb100' )
#             logger.info('flg_changed_timezone: %s' % flg_changed_timezone)
#
#             self.exchange.order("S200"+str(self.idx), False, lot*2, limit=fb200, when=(S200 is None or flg_changed_timezone), post_only=True)
#             self.exchange.order("S162"+str(self.idx), False, lot*1, limit=fb162, when=(S162 is None or flg_changed_timezone), post_only=True)
#             self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, when=(S138 is None or flg_changed_timezone), post_only=True)
#             self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, when=(S100 is None or flg_changed_timezone), post_only=True)
#
#         L0_w = bitmex.get_open_order("L0_w"+str(self.idx))
#         L038_w = bitmex.get_open_order("L038_w"+str(self.idx))
#         L062_w = bitmex.get_open_order("L062_w"+str(self.idx))
#         L0100_w = bitmex.get_open_order("L0100_w"+str(self.idx))
#
#         S100_w = bitmex.get_open_order("S100_w"+str(self.idx))
#         S138_w = bitmex.get_open_order("S138_w"+str(self.idx))
#         S162_w = bitmex.get_open_order("S162_w"+str(self.idx))
#         S200_w = bitmex.get_open_order("S200_w"+str(self.idx))
#
#
#         # win order of stoplimit
#         if price <= fb0: #and L0 is None:
#             self.exchange.order("L0_w"+str(self.idx), False, lot*1, limit=fb38, stop=fb0)  # post_only=True)
#             logger.info('rice <= fb0: %s' % fb0)
#         if price <= fb038: # and L038 is None:
#             self.exchange.order("L038_w"+str(self.idx), False, lot*1, limit=fb0, stop=fb038)
#             logger.info('price <= fb038: %s' % fb038)
#         if price <= fb062: # and L062 is None:
#             self.exchange.order("L062_w"+str(self.idx), False, lot*1, limit=fb038, stop=fb062)
#             logger.info('price <= fb062: %s' % fb062)
#         if price <= fb0100: # and L0100 is None:
#             self.exchange.order("L0100_w"+str(self.idx), False, lot*2, limit=fb062, stop=fb0100)
#             logger.info('price <= fb0100: %s' % fb0100)
#
#
#         if price >= fb100: # and S100 is None:
#             logger.info('price >= fb100: %s' % fb100)
#             self.exchange.order("S100_w"+str(self.idx), True, lot*1, limit=fb62, stop=fb0100)
#         if price >= fb138: # and S138 is None:
#             self.exchange.order("S138_w"+str(self.idx), True, lot*1, limit=fb100, stop=fb138)
#             logger.info('price >= fb138: %s' % fb138)
#         if price >=fb162: # and S162 is None:
#             self.exchange.order("S162_w"+str(self.idx), True, lot*1, limit=fb138, stop=fb162)
#             logger.info('price >= fb162 %s' % fb162)
#         if price >= fb200: # and S200 is None:
#             self.exchange.order("S200_w"+str(self.idx), True, lot*2, limit=fb162, stop=fb200)
#             logger.info('price >= fb200: %s' % fb200)
#
#         # logger.info('bitmex.get_margin():%s' % bitmex.get_margin())
#         # logger.info('bitmex.get_position():%s' % bitmex.get_position())
#
#         self.pre_fb0 = fb0
#         self.pre_fb100 = fb100
#
#         # for debug
#         logger.info('fb200: %s' % fb200)
#         logger.info('fb162: %s' % fb162)
#         logger.info('fb138: %s' % fb138)
#         logger.info('fb100: %s' % fb100)
#         logger.info('fb62: %s' % fb62)
#         logger.info('fb50: %s' % fb50)
#         logger.info('fb38: %s' % fb38)
#         logger.info('fb0: %s' % fb0)
#         logger.info('fb038: %s' % fb038)
#         logger.info('fb062: %s' % fb062)
#         logger.info('fb0100: %s' % fb0100)
#
#         diff = (abs(bitmex.get_balance() - abs(self.prebalance)))
#
#         realised_pnl = bitmex.get_margin()['realisedPnl']
#
#         logger.info('prebalance():%s' % self.prebalance)
#         logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
#         logger.info('diff:%s' % diff)
#         logger.info('realised_pnl:%s' % realised_pnl)
#
#         logger.info('--------------------------------------------------')


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
class R2H5(Bot):
    variants = [sma, ema, double_ema, triple_ema, wma, ssma, hull, heikinashi]
    eval_time = None

    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'fast_len': hp.quniform('fast_len', 1, 60, 1),
            'slow_len': hp.quniform('slow_len', 1, 240, 1),
        }

    def strategy(self, open, close, high, low, volume):

        lot = self.exchange.get_lot()
        # for test
        # lot = int(round(lot / 2))
        # lot = 10
        logger.info('lot:%s' % lot)
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        resolution = self.input(defval=1, title="resolution", type=int)
        variant_type = self.input(defval=5, title="variant_type", type=int)
        basis_len = self.input(defval=19,  title="basis_len", type=int)
        logger.info('price:%s\n' % price)

        # fast_len = self.input('fast_len', int, 1)
        # slow_len = self.input('slow_len', int, 21)
        # trend_len = self.input('slow_len', int, 55)
        # longtrend_len = self.input('slow_len', int, 233)

        # fast_len = self.input('fast_len', int, 1)
        # slow_len = self.input('slow_len', int, 55)
        # trend_len = self.input('slow_len', int, 240)
        # longtrend_len = self.input('slow_len', int, 233)


        fast_len = self.input('fast_len', int, 1)
        slow_len = self.input('slow_len', int, 30)
        trend_len = self.input('slow_len', int, 60)
        longtrend_len = self.input('slow_len', int, 120)
        logger.info('fast_len:%s' % fast_len)
        logger.info('slow_len:%s' % slow_len)
        logger.info('trend_len:%s' % trend_len)
        logger.info('longtrend_len:%s' % longtrend_len)


        # for various minutes source
        source = self.exchange.security(str(resolution) + 'm')

        hadf = heikinashi(source)
        hadf_fast = heikinashi(hadf)

        ha_open_values = hadf_fast['HA_open'].values
        ha_close_values = hadf_fast['HA_close'].values
        variant = self.variants[variant_type]

        ha_open_fast = variant(ha_open_values,  fast_len)
        ha_close_fast = variant(ha_close_values, fast_len)
        haopen_fast = ha_open_fast[-1]
        haclose_fast = ha_close_fast[-1]
        haup_fast = haclose_fast > haopen_fast
        hadown_fast = haclose_fast <= haopen_fast
        logger.info('haup_fast:%s\n' % haup_fast)


        ha_open_slow = variant(ha_open_values,  slow_len)
        ha_close_slow = variant(ha_close_values, slow_len)
        haopen_slow = ha_open_slow[-1]
        haclose_slow = ha_close_slow[-1]
        haup_slow = haclose_slow > haopen_slow
        hadown_slow = haclose_slow <= haopen_slow
        logger.info('haup_slow:%s\n' % haup_slow)


        ha_open_trend = variant(ha_open_values,  trend_len)
        ha_close_trend = variant(ha_close_values, trend_len)
        haopen_trend = ha_open_trend[-1]
        haclose_trend = ha_close_trend[-1]
        haup_trend = haclose_trend > haopen_trend
        hadown_trend = haclose_trend <= haopen_trend
        logger.info('haup_trend:%s\n' % haup_trend)

        ha_open_longtrend = variant(ha_open_values,  longtrend_len)
        ha_close_longtrend = variant(ha_close_values, longtrend_len)
        haopen_longtrend = ha_open_longtrend[-1]
        haclose_longtrend = ha_close_longtrend[-1]
        haup_longtrend = haclose_longtrend > haopen_longtrend
        hadown_longtrend = haclose_longtrend <= haopen_longtrend
        logger.info('haup_longtrend:%s\n' % haup_longtrend)


        # resol_fast = self.input(defval=1, title="resolution", type=int)  # defval 변경, 예) 5분 --> 5
        # source_fast = self.exchange.security(str(resol_fast) + 'm')  # init  참고
        # hadf_fast = heikinashi(source_fast, 1)
        # haopen_fast = hadf_fast['HA_open'][-1]
        # haclose_fast = hadf_fast['HA_close'][-1]
        # haup_fast = haclose_fast > haopen_fast
        # hadown_fast = haclose_fast <= haopen_fast
        # logger.info('haup_fast:%s\n' % haup_fast)
        # logger.info('hadown_fast:%s\n' % hadown_fast)


        # resol_slow = self.input(defval=4, title="resolution", type=int)  # defval 변경, 예) 5분 --> 5
        # source_slow = self.exchange.security(str(resol_slow) + 'h')  # init  참고
        # hadf_slow = heikinashi(source_slow, 1)
        # haopen_slow = hadf_slow['HA_open'][-1]
        # haclose_slow = hadf_slow['HA_close'][-1]
        # haup_slow = haclose_slow > haopen_slow
        # hadown_slow = haclose_slow <= haopen_slow
        # logger.info('haup_slow:%s\n' % haup_slow)
        # logger.info('hadown_slow:%s\n' % hadown_slow)


        # resol_trend = self.input(defval=1, title="resolution", type=int)  # defval 변경, 예) 5분 --> 5
        # source_trend = self.exchange.security(str(resol_trend) + 'd')  # init  참고:wq!:wq!
        # hadf_trend = heikinashi(source_trend)
        # haopen_trend = hadf_trend['HA_open'][-1]
        # haclose_trend = hadf_trend['HA_close'][-1]
        # haup_trend = haclose_trend > haopen_trend
        # hadown_trend = haclose_trend <= haopen_trend
        # logger.info('haup_trend:%s\n' % haup_trend)
        # logger.info('hadown_trend:%s\n' % hadown_slow)


        " long "
        self.exchange.entry("Long", True, lot, when=crossover(ha_close_longtrend, ha_open_longtrend))
        " short "
        self.exchange.entry("Short", False, lot, when=crossunder(ha_close_longtrend, ha_open_longtrend))


        # source_entry = self.exchange.security('1h')
        #
        # hadf_entry = heikinashi(source_entry)
        # hadf_trading = heikinashi(hadf_entry)
        #
        # ha_open_longtrend_entry = variant(ha_open_values,  2)  # 2h
        # ha_close_longtrend_entry = variant(ha_close_values, 2)
        #
        # haopen_longtrend_entry = ha_open_longtrend_entry[-1]
        # haclose_longtrend_entry = ha_close_longtrend_entry[-1]
        # haup_longtrend_entry = haclose_longtrend_entry > haopen_longtrend_entry
        # hadown_longtrend_entry = haclose_longtrend_entry <= haopen_longtrend_entry
        #
        # logger.info('1h기준 2h\n')
        # logger.info('haup_longtrend_enty:%s\n' % haup_longtrend_entry)
        # logger.info('hadown_longtrend_entry:%s\n' % hadown_longtrend_entry)
        #
        # " long "
        # self.exchange.entry("Long", True, lot, when=crossover(ha_close_longtrend_entry, ha_open_longtrend_entry))
        # " short "
        # self.exchange.entry("Short", False, lot, when=crossunder(ha_close_longtrend_entry, ha_open_longtrend_entry))

# heikinashi
class Heikinashi(Bot):
    variants = [sma, ema, double_ema, triple_ema, wma, ssma, hull, heikinashi]
    eval_time = None

    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'fast_len': hp.quniform('fast_len', 1, 60, 1),
            'slow_len': hp.quniform('slow_len', 1, 240, 1),
        }

    def strategy(self, open, close, high, low, volume):

        lot = self.exchange.get_lot()
        # for test
        # lot = int(round(lot / 2))
        # lot = 10
        logger.info('lot:%s' % lot)
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        resolution = self.input(defval=1, title="resolution", type=int)
        variant_type = self.input(defval=5, title="variant_type", type=int)
        basis_len = self.input(defval=19,  title="basis_len", type=int)
        logger.info('price:%s\n' % price)

        # fast_len = self.input('fast_len', int, 1)
        # slow_len = self.input('slow_len', int, 21)
        # trend_len = self.input('slow_len', int, 55)
        # longtrend_len = self.input('slow_len', int, 233)

        # fast_len = self.input('fast_len', int, 1)
        # slow_len = self.input('slow_len', int, 55)
        # trend_len = self.input('slow_len', int, 240)
        # longtrend_len = self.input('slow_len', int, 233)


        fast_len = self.input('fast_len', int, 1)
        slow_len = self.input('slow_len', int, 30)
        trend_len = self.input('slow_len', int, 60)
        longtrend_len = self.input('slow_len', int, 120)
        logger.info('fast_len:%s' % fast_len)
        logger.info('slow_len:%s' % slow_len)
        logger.info('trend_len:%s' % trend_len)
        logger.info('longtrend_len:%s' % longtrend_len)


        # for various minutes source
        source = self.exchange.security(str(resolution) + 'm')

        hadf = heikinashi(source)
        hadf_fast = heikinashi(hadf)

        ha_open_values = hadf_fast['HA_open'].values
        ha_close_values = hadf_fast['HA_close'].values
        variant = self.variants[variant_type]

        ha_open_fast = variant(ha_open_values,  fast_len)
        ha_close_fast = variant(ha_close_values, fast_len)
        haopen_fast = ha_open_fast[-1]
        haclose_fast = ha_close_fast[-1]
        haup_fast = haclose_fast > haopen_fast
        hadown_fast = haclose_fast <= haopen_fast
        logger.info('haup_fast:%s\n' % haup_fast)


        ha_open_slow = variant(ha_open_values,  slow_len)
        ha_close_slow = variant(ha_close_values, slow_len)
        haopen_slow = ha_open_slow[-1]
        haclose_slow = ha_close_slow[-1]
        haup_slow = haclose_slow > haopen_slow
        hadown_slow = haclose_slow <= haopen_slow
        logger.info('haup_slow:%s\n' % haup_slow)


        ha_open_trend = variant(ha_open_values,  trend_len)
        ha_close_trend = variant(ha_close_values, trend_len)
        haopen_trend = ha_open_trend[-1]
        haclose_trend = ha_close_trend[-1]
        haup_trend = haclose_trend > haopen_trend
        hadown_trend = haclose_trend <= haopen_trend
        logger.info('haup_trend:%s\n' % haup_trend)

        ha_open_longtrend = variant(ha_open_values,  longtrend_len)
        ha_close_longtrend = variant(ha_close_values, longtrend_len)
        haopen_longtrend = ha_open_longtrend[-1]
        haclose_longtrend = ha_close_longtrend[-1]
        haup_longtrend = haclose_longtrend > haopen_longtrend
        hadown_longtrend = haclose_longtrend <= haopen_longtrend
        logger.info('haup_longtrend:%s\n' % haup_longtrend)


        # resol_fast = self.input(defval=1, title="resolution", type=int)  # defval 변경, 예) 5분 --> 5
        # source_fast = self.exchange.security(str(resol_fast) + 'm')  # init  참고
        # hadf_fast = heikinashi(source_fast, 1)
        # haopen_fast = hadf_fast['HA_open'][-1]
        # haclose_fast = hadf_fast['HA_close'][-1]
        # haup_fast = haclose_fast > haopen_fast
        # hadown_fast = haclose_fast <= haopen_fast
        # logger.info('haup_fast:%s\n' % haup_fast)
        # logger.info('hadown_fast:%s\n' % hadown_fast)


        # resol_slow = self.input(defval=4, title="resolution", type=int)  # defval 변경, 예) 5분 --> 5
        # source_slow = self.exchange.security(str(resol_slow) + 'h')  # init  참고
        # hadf_slow = heikinashi(source_slow, 1)
        # haopen_slow = hadf_slow['HA_open'][-1]
        # haclose_slow = hadf_slow['HA_close'][-1]
        # haup_slow = haclose_slow > haopen_slow
        # hadown_slow = haclose_slow <= haopen_slow
        # logger.info('haup_slow:%s\n' % haup_slow)
        # logger.info('hadown_slow:%s\n' % hadown_slow)


        # resol_trend = self.input(defval=1, title="resolution", type=int)  # defval 변경, 예) 5분 --> 5
        # source_trend = self.exchange.security(str(resol_trend) + 'd')  # init  참고:wq!:wq!
        # hadf_trend = heikinashi(source_trend)
        # haopen_trend = hadf_trend['HA_open'][-1]
        # haclose_trend = hadf_trend['HA_close'][-1]
        # haup_trend = haclose_trend > haopen_trend
        # hadown_trend = haclose_trend <= haopen_trend
        # logger.info('haup_trend:%s\n' % haup_trend)
        # logger.info('hadown_trend:%s\n' % hadown_slow)


        " long "
        self.exchange.entry("Long", True, lot, when=crossover(ha_close_longtrend, ha_open_longtrend))
        " short "
        self.exchange.entry("Short", False, lot, when=crossunder(ha_close_longtrend, ha_open_longtrend))


        # source_entry = self.exchange.security('1h')
        #
        # hadf_entry = heikinashi(source_entry)
        # hadf_trading = heikinashi(hadf_entry)
        #
        # ha_open_longtrend_entry = variant(ha_open_values,  2)  # 2h
        # ha_close_longtrend_entry = variant(ha_close_values, 2)
        #
        # haopen_longtrend_entry = ha_open_longtrend_entry[-1]
        # haclose_longtrend_entry = ha_close_longtrend_entry[-1]
        # haup_longtrend_entry = haclose_longtrend_entry > haopen_longtrend_entry
        # hadown_longtrend_entry = haclose_longtrend_entry <= haopen_longtrend_entry
        #
        # logger.info('1h기준 2h\n')
        # logger.info('haup_longtrend_enty:%s\n' % haup_longtrend_entry)
        # logger.info('hadown_longtrend_entry:%s\n' % hadown_longtrend_entry)
        #
        # " long "
        # self.exchange.entry("Long", True, lot, when=crossover(ha_close_longtrend_entry, ha_open_longtrend_entry))
        # " short "
        # self.exchange.entry("Short", False, lot, when=crossunder(ha_close_longtrend_entry, ha_open_longtrend_entry))



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

        print(lot)

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
        }

    def strategy(self, open, close, high, low, volume):
        self.start += 1
        flg_changed_timezone = False
        lot = self.exchange.get_lot()
        # for test lot
        lot = int(round(lot / 50))
        # lot = 1
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        resolution = self.input(defval=10, title="resolution", type=int) # defval 변경, 예) 5분 --> 5, 'm' or 1시간  1, 'h', 1Day 1, 'd'
        source = self.exchange.security(str(resolution) + 'm')  # def __init__  비교
        series_high = source['high'].values
        series_low = source['low'].values
        fb100 = last(highest(series_high, 1))  # 1시간 1, 1D의 경우는 resolution도 변경
        fb0 = last(lowest(series_low, 1))

        # logger.info('source: %s' % source)
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


        fb262 = math.ceil((fb100 - fb0) * 1.628 + fb100)
        fb200 = math.ceil((fb100 - fb0) * 1.0 + fb100)
        # fb162 = math.ceil((fb100 - fb0) * 0.618 + fb100)
        fb138 = math.ceil((fb100 - fb0) * 0.382 + fb100)

        fb62 = math.ceil((fb100 - fb0) * 0.618 + fb0)
        fb50 = math.ceil((fb100 - fb0) / 2 + fb0)
        fb38 = math.ceil((fb100 - fb0) * 0.382 + fb0)

        fb038 = math.ceil(fb0 - (fb100 - fb0) * 0.382)
        # fb062 = math.ceil(fb0 - (fb100 - fb0) * 0.618)
        fb0100 = math.ceil(fb0 - (fb100 - fb0) * 1.00)
        fb0162 = math.ceil(fb0 - (fb100 - fb0) * 1.60)

        qty= bitmex.get_position_size()
        logger.info('current position qty: %s' % qty)

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

        if self.pre_fb0 != 0 and fb0 != self.pre_fb0 and fb100 != self.pre_fb100 :
            flg_changed_timezone = True
            logger.info('+++++++ flg_changed_timezone: %s' % flg_changed_timezone)
            logger.info('cancel_all orders because new time zone')

        # when this program start, execute only once
        if self.start == 1 or flg_changed_timezone:

            self.exchange.cancel_all()
            stopprice = price
            if bitmex.get_whichpositon() == 'LONG':
                if price > fb50:
                    stopprice = fb50
                    logger.info('fb50')
                else:
                    stopprice = fb0
                    logger.info('fb0')
                logger.info('CL000 stopprice: %s' % stopprice)
                logger.info('CL000 --> Clear Long')
                self.exchange.order("CL000", False, qty, limit=stopprice, post_only=True)
                pass
            elif bitmex.get_whichpositon() == 'SHORT':
                if price <= fb50:
                    stopprice = fb50
                    logger.info('fb50')

                else:
                    stopprice = fb100
                    logger.info('fb100')

                logger.info('CS000 stopprice: %s' % stopprice)
                self.exchange.order("CS000", True, qty, limit=stopprice, post_only=True)
            else:
                logger.info('else case when self.start == 1 or flg_changed_timezone: %s ' % bitmex.get_whichpositon())
                pass

            # short position
            self.exchange.order("S262"+str(self.idx), False, lot*3, limit=fb262, post_only=True)
            self.exchange.order("S200"+str(self.idx), False, lot*2, limit=fb200, post_only=True)
            # self.exchange.order("S162"+str(self.idx), False, lot*2, limit=fb162, post_only=True)
            self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, post_only=True)
            # self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, post_only=True)

            # long position
            # self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, post_only=True)
            self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, post_only=True)
            # self.exchange.order("L062"+str(self.idx), True, lot*2, limit=fb062, post_only=True)
            self.exchange.order("L0100"+str(self.idx), True, lot*2, limit=fb0100, post_only=True)
            self.exchange.order("L0162"+str(self.idx), True, lot*3, limit=fb0162, post_only=True)

        if flg_changed_timezone is True:
            self.idx += 1

        L0 = bitmex.get_open_order("L0"+str(self.idx))
        L038 = bitmex.get_open_order("L038"+str(self.idx))
        # L062 = bitmex.get_open_order("L062"+str(self.idx))
        L0100 = bitmex.get_open_order("L0100"+str(self.idx))
        L0162 = bitmex.get_open_order("L0162"+str(self.idx))

        S262 = bitmex.get_open_order("S262"+str(self.idx))
        S200 = bitmex.get_open_order("S200"+str(self.idx))
        # S162 = bitmex.get_open_order("S162"+str(self.idx))
        S138 = bitmex.get_open_order("S138"+str(self.idx))
        S100 = bitmex.get_open_order("S100"+str(self.idx))

        S262_w = bitmex.get_open_order("S262_w"+str(self.idx))
        S200_w = bitmex.get_open_order("S200_w"+str(self.idx))
        # S162_w = bitmex.get_open_order("S162_w"+str(self.idx))
        S138_w = bitmex.get_open_order("S138_w"+str(self.idx))
        S100_w = bitmex.get_open_order("S100_w"+str(self.idx))


        L0_w = bitmex.get_open_order("L0_w"+str(self.idx))
        L038_w = bitmex.get_open_order("L038_w"+str(self.idx))
        # L062_w = bitmex.get_open_order("L062_w"+str(self.idx))
        L0100_w = bitmex.get_open_order("L0100_w"+str(self.idx))
        L0162_w = bitmex.get_open_order("L0162_w"+str(self.idx))

        #
        # logger.info('(L0 is None): %s' % (L0 is None))


        # new entry order
        # new short position
        # if flg_changed_timezone or price < fb100:
        #     self.exchange.order("S262"+str(self.idx), False, lot*2, limit=fb262, when=(S262 is None), post_only=True)
        #     self.exchange.order("S200"+str(self.idx), False, lot*1, limit=fb200, when=(S200 is None), post_only=True)
        #     # self.exchange.order("S162"+str(self.idx), False, lot*2, limit=fb162, when=(S162 is None), post_only=True)
        #     self.exchange.order("S138"+str(self.idx), False, lot*1, limit=fb138, when=(S138 is None), post_only=True)
        #     # self.exchange.order("S100"+str(self.idx), False, qS100, limit=fb100, when=(S100 is None), post_only=True)
        #
        # # new long position
        # if flg_changed_timezone or price > fb0:
        #     # self.exchange.order("L0"+str(self.idx), True, qL0, limit=fb0, when=(L0 is None), post_only=True)
        #     self.exchange.order("L038"+str(self.idx), True, lot*1, limit=fb038, when=(L038 is None), post_only=True)
        #     # self.exchange.order("L062"+str(self.idx), True, lot*1, limit=fb062, when=(L062 is None), post_only=True)
        #     self.exchange.order("L0100"+str(self.idx), True, lot*1, limit=fb0100, when=(L0100 is None), post_only=True)
        #     self.exchange.order("L0162"+str(self.idx), True, lot*2, limit=fb0162, when=(L0162 is None), post_only=True)

        # self.exchange.order("L038_w"+str(self.idx), False, lot*1, limit=fb0, when=fb038, post_only=True)
        # self.exchange.order("L0100_w" + str(self.idx), False, lot * 1, limit=fb038,  when=fb0100, post_only=True)
        # self.exchange.order("L0160_w" + str(self.idx), False, lot * 2, limit=fb0100,  when=fb0162, post_only=True)
        #
        # self.exchange.order("S138_w" + str(self.idx), True, lot * 1, limit=fb100,  when=fb138, post_only=True)
        # self.exchange.order("S200_w" + str(self.idx), True, lot * 1, limit=fb138,  when=fb200, post_only=True)
        # self.exchange.order("S262_w" + str(self.idx), True, lot * 2, limit=fb200,  when=fb262, post_only=True)

        # stop order
        # if price < fb0 and L0 is None:
        #     self.exchange.order("L0_w"+str(self.idx), False, lot*1, limit=fb38, post_only=True)
        #     logger.info('rice <= fb0: %s' % fb0)
        if price <= fb038 and L038 is None:
            self.exchange.order("L038_w"+str(self.idx), False, lot*1, limit=fb0, post_only=True)
            logger.info('price <= fb038: %s' % fb038)
        # if price < fb062 and L062 is None:
        #     self.exchange.order("L062_w"+str(self.idx), False, lot*2, limit=fb038, post_only=True)
        #     logger.info('price <= fb062: %s' % fb062)
        if price <= fb0100 and L0100 is None:
            self.exchange.order("L0100_w"+str(self.idx), False, lot*1, limit=fb038, post_only=True)
            logger.info('price <= fb0100: %s' % fb0100)
        if price <= fb0162 and L0162 is not None:
            self.exchange.order("L0100_w"+str(self.idx), False, lot*2, limit=fb100, post_only=True)
            logger.info('price <= fb0162: %s' % fb0162)


        # if price > fb100 and S100 is None:
        #     logger.info('price >= fb100: %s' % fb100)
        #     self.exchange.order("S100_w"+str(self.idx), True, lot*1, limit=fb62, post_only=True)
        if price >= fb138 and S138 is None:
            self.exchange.order("S138_w"+str(self.idx), True, lot*1, limit=fb100, post_only=True)
            logger.info('price >= fb138: %s' % fb138)
        # if price > fb162 and S162 is None:
        #     self.exchange.order("S162_w"+str(self.idx), True, lot*2, limit=fb138, post_only=True)
        #     logger.info('price >= fb162 %s' % fb162)
        if price >= fb200 and S200 is None:
            self.exchange.order("S200_w"+str(self.idx), True, lot*1, limit=fb138, post_only=True)
            logger.info('price >= fb200: %s' % fb200)
        if price >= fb262 and S262 is None:
            self.exchange.order("S262_w"+str(self.idx), True, lot*2, limit=fb200, post_only=True)
        #     logger.info('price >= fb262: %s' % fb262)

        # logger.info('bitmex.get_margin():%s' % bitmex.get_margin())
        # logger.info('bitmex.get_position():%s' % bitmex.get_position())

        # save pre-timezone's fb0, fb100 values
        self.pre_fb0 = fb0
        self.pre_fb100 = fb100

        # for debug
        logger.info('fb200: %s' % fb200)
        # logger.info('fb162: %s' % fb162)
        logger.info('fb138: %s' % fb138)
        logger.info('fb100: %s' % fb100)
        logger.info('fb62: %s' % fb62)
        logger.info('fb50: %s' % fb50)
        logger.info('fb38: %s' % fb38)
        logger.info('fb0: %s' % fb0)
        logger.info('fb038: %s' % fb038)
        # logger.info('fb062: %s' % fb062)
        logger.info('fb0100: %s' % fb0100)

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))

        realised_pnl = bitmex.get_margin()['realisedPnl']

        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)

        logger.info('--------------------------------------------------')

class R2H5(Bot):
    prebalance = BitMex(threading=False).get_balance()
    start = 0
    pre_fb0 = 0
    pre_fb100 = 0
    idx = 0
    stratey_mode = 'R2'  # or H5

    variants = [sma, ema, double_ema, triple_ema, wma, ssma, hull, heikinashi]
    eval_time = None

    def __init__(self):
        Bot.__init__(self, '1m')

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
        }

    def strategy(self, open, close, high, low, volume):
        logger.info('-------------------------strategy start-----------------------\n')
        lot = self.exchange.get_lot()
        # for test
        lot = int(round(lot / 2))
        lot = 10
        logger.info('lot:%s' % lot)
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()
        logger.info('price:%s\n' % price)

        fast_len = self.input('fast_len', int, 20)
        slow_len = self.input('slow_len', int, 120)
        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)

        # sma
        # for i in range(1, 5):
        #     logger.info('fast_sma 20 [%s] *******: %s' % (-i, fast_sma[-i]))
        # logger.info('slow_sma 120  ******: %s' % slow_sma[-1])

        # rsi
        rsi_len = self.input('rsi_len', int, 2)
        fast_rsi = rsi(close, rsi_len)
        rsi_stoplen = self.input('rsi_len', int, 5)
        fast_slow_rsi = rsi(close, rsi_len)

        for i in range(1, 21):
            if fast_rsi[-i] >= 95:
                logger.info('fast_rsi2 ***** [%s]: %s >= 95' % (-i, fast_rsi[-i]))
            elif fast_rsi[-i] <= 5:
                logger.info('fast_rsi2 ***** [%s]: %s <= 5' % (-i, fast_rsi[-i]))
            else:
                logger.info('fast_rsi2 ***** [%s]: %s' % (-i, fast_rsi[-i]))

        # willr
        slow_willr = willr(high, low, close, period=960)
        logger.info('fast_willr ***** %s' % slow_willr[-1])
        # bband
        # bband_len = self.input('bbandup_len', int, 20)
        # bbup, bbmid, bblow = bbands(close, timeperiod=bband_len, nbdevup=2, nbdevdn=2, matype=0)
        # for i in range(1, 2):
        #     logger.info('fast_bband ***** [%s], bbup: %s, bbmid: %s, bblow: %s' % (-i, bbup[-i], bbmid[-i], bblow[-i]))

        # heikinashi
        resolution = self.input(defval=1, title="resolution", type=int)
        variant_type = self.input(defval=5, title="variant_type", type=int)
        source = self.exchange.security(str(resolution) + 'm')

        fast_len = self.input('fast_len', int, 1)
        middle_len = self.input('middle_len', int, 5)
        slow_len = self.input('slow_len', int, 30)
        trend_len = self.input('slow_len', int, 60)
        longtrend_len = self.input('slow_len', int, 120)
        longlongtrend_len = self.input('slow_len', int, 240)

        hadf = heikinashi(source)
        hadf_fast = heikinashi(hadf)

        ha_open_values = hadf_fast['HA_open'].values
        ha_close_values = hadf_fast['HA_close'].values
        variant = self.variants[variant_type]

        ha_open_fast = variant(ha_open_values,  fast_len)
        ha_close_fast = variant(ha_close_values, fast_len)
        haopen_fast = ha_open_fast[-1]
        haclose_fast = ha_close_fast[-1]
        haup_fast = haclose_fast > haopen_fast
        hadown_fast = haclose_fast <= haopen_fast
        logger.info('haup_fast:%s' % haup_fast)

        ha_open_middle = variant(ha_open_values,  middle_len)
        ha_close_middle = variant(ha_close_values, middle_len)
        haopen_middle = ha_open_middle[-1]
        haclose_middle = ha_close_middle[-1]
        haup_middle = haclose_middle > haopen_middle
        hadown_middle = haclose_middle <= haopen_middle
        logger.info('haup_middle:%s' % haup_middle)


        ha_open_slow = variant(ha_open_values,  slow_len)
        ha_close_slow = variant(ha_close_values, slow_len)
        haopen_slow = ha_open_slow[-1]
        haclose_slow = ha_close_slow[-1]
        haup_slow = haclose_slow > haopen_slow
        hadown_slow = haclose_slow <= haopen_slow
        logger.info('haup_slow:%s' % haup_slow)


        ha_open_trend = variant(ha_open_values,  trend_len)
        ha_close_trend = variant(ha_close_values, trend_len)
        haopen_trend = ha_open_trend[-1]
        haclose_trend = ha_close_trend[-1]
        haup_trend = haclose_trend > haopen_trend
        hadown_trend = haclose_trend <= haopen_trend
        logger.info('haup_trend:%s' % haup_trend)

        ha_open_longtrend = variant(ha_open_values,  longtrend_len)
        ha_close_longtrend = variant(ha_close_values, longtrend_len)
        haopen_longtrend = ha_open_longtrend[-1]
        haclose_longtrend = ha_close_longtrend[-1]
        haup_longtrend = haclose_longtrend > haopen_longtrend
        hadown_longtrend = haclose_longtrend <= haopen_longtrend
        logger.info('haup_longtrend:%s\n' % haup_longtrend)


        ha_open_longlongtrend = variant(ha_open_values,  longlongtrend_len)
        ha_close_longlongtrend = variant(ha_close_values, longlongtrend_len)
        haopen_longlongtrend = ha_open_longlongtrend[-1]
        haclose_longlongtrend = ha_close_longlongtrend[-1]
        haup_longlongtrend = haclose_longlongtrend > haopen_longlongtrend
        hadown_longlongtrend = haclose_longlongtrend <= haopen_longlongtrend
        logger.info('haup_longlongtrend:%s\n' % haup_longlongtrend)


        # resolutionh = self.input(defval=1, title="resolution", type=int)
        # variant_type = self.input(defval=5, title="variant_type", type=int)
        # sourceh = self.exchange.security(str(resolutionh) + 'h')
        #
        # hadf_h = heikinashi(sourceh)
        # hadf_longtrend_h = heikinashi(hadf_h)
        #
        # ha_open_values_h = hadf_longtrend_h['HA_open'].values
        # ha_close_values_h = hadf_longtrend_h['HA_close'].values
        # variant = self.variants[variant_type]
        #
        # ha_open_longtrend_h = variant(ha_open_values_h,  4)  # 1시간 1, 2시간 2
        # ha_close_longtrend_h = variant(ha_close_values_h, 4)
        # haopen_longtrend_h = ha_open_longtrend_h[-1]
        # haclose_longtrend_h = ha_close_longtrend_h[-1]
        # haup_longtrend_h = haclose_longtrend_h > haopen_longtrend_h
        # hadown_longtrend_h = haclose_longtrend_h <= haopen_longtrend_h
        # # logger.info('haup_longtrend_h:%s\n' % haup_longtrend_h)

        self.start += 1
        flg_changed_timezone = False
        lot = self.exchange.get_lot()
        # for test lot
        lot = int(round(lot / 10))
        # lot = 1
        bitmex = BitMex(threading=False)
        price = bitmex.get_market_price()

        resolution = self.input(defval=1, title="resolution", type=int) # defval 변경, 예) 5분 --> 5, 'm' or 1시간  1, 'h', 1Day 1, 'd'
        source = self.exchange.security(str(resolution) + 'h')  # def __init__  비교
        series_high = source['high'].values
        series_low = source['low'].values
        fb100 = last(highest(series_high, 1))  # 1시간 1, 1D의 경우는 resolution도 변경
        fb0 = last(lowest(series_low, 1))

        # for test
        # fb100 = price + 15
        # fb0 = price - 15

        # fb262 = math.ceil((fb100 - fb0) * 1.628 + fb100)
        # fb200 = math.ceil((fb100 - fb0) * 1.0 + fb100)
        # fb162 = math.ceil((fb100 - fb0) * 0.618 + fb100)
        # fb138 = math.ceil((fb100 - fb0) * 0.382 + fb100)

        fb62 = math.ceil((fb100 - fb0) * 0.618 + fb0)
        fb50 = math.ceil((fb100 - fb0) / 2 + fb0)
        fb38 = math.ceil((fb100 - fb0) * 0.382 + fb0)

        # fb038 = math.ceil(fb0 - (fb100 - fb0) * 0.382)
        # fb062 = math.ceil(fb0 - (fb100 - fb0) * 0.618)
        # fb0100 = math.ceil(fb0 - (fb100 - fb0) * 1.00)
        # fb0162 = math.ceil(fb0 - (fb100 - fb0) * 1.60)

        qty= bitmex.get_position_size()
        logger.info('current position qty: %s' % qty)

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

        if self.pre_fb0 != 0 and fb0 != self.pre_fb0 and fb100 != self.pre_fb100:
            flg_changed_timezone = True
            logger.info('+++++++ flg_changed_timezone: %s' % flg_changed_timezone)
            logger.info('cancel_all orders because new time zone')

        # when this program start, execute only once
        # if self.start == 1 or flg_changed_timezone:

        # for debug
        logger.info('fb100: %s' % fb100)
        logger.info('fb62: %s' % fb62)
        # logger.info('fb50: %s' % fb50)
        logger.info('fb38: %s' % fb38)
        logger.info('fb0: %s' % fb0)

        logger.info('bitmex.get_open_order(Long): %s ' % bitmex.get_open_order('Long'))
        logger.info('bitmex.get_open_order(Short): %s ' % bitmex.get_open_order('Short'))
        logger.info('bitmex.get_open_order(LCatch): %s ' % bitmex.get_open_order('LCatch'))
        logger.info('bitmex.get_open_order(SCatch): %s ' % bitmex.get_open_order('SCatch'))

        if self.stratey_mode == 'R2':
            logger.info('=============== stratey_mode = R2 ==============')

            if self.start == 1:
                self.exchange.cancel_all()
            # 공격적인 로직 추가시
            # if haup_middle and haup_slow and haup_trend and haup_longtrend and fast_rsi[-1] <= 20:  # entry long condition on Short Trend
            #     logger.info('Now Short conditions: fast_rsi[-1] <= 10 0k -->  %s' % fast_rsi[-1])
            #     self.exchange.order('Long', True, lot, limit=price - 0.5, post_only=True)
            # elif hadown_middle and hadown_slow and hadown_trend and hadown_longtrend and fast_rsi[-1] >= 80:  # # entry short condition on Long Trend
            #     logger.info('Now Long conditions: fast_rsi[-1] >= 90 0k -->  %s' % fast_rsi[-1])
            #     self.exchange.order('Short', False, lot, limit=price + 0.5, post_only=True)

            # 일반적인 로직
            if bitmex.get_whichpositon() == 'LONG':
                logger.info('---------------------->>LONG order status')
                logger.info('ordered price:%s' % bitmex.get_position_avg_price())
                if fast_rsi[-1] >= 95:  # 스탑로직
                    logger.info('>>fast_rsi[-1] >= 95')
                    self.exchange.order('StopLong', False, qty, limit=price + 0.5, post_only=True)
                elif hadown_slow and hadown_trend:  # 손절로직
                    logger.info('>>hadown_trend and hadown_longtrend Long -> Short : slow trend changed')
                    self.exchange.close_all()
                    self.exchange.cancel_all()

                    # # 돌파로직
                    # if hadown_fast and hadown_middle and hadown_slow:  # 모두 숏이면
                    #     self.exchange.order('ChBrkShort', False, qty*2)
                    #     self.exchange.cancel_all()
                    # else:
                    #     self.exchange.close_all()
                # elif hadown_trend and hadown_longtrend:  # 손절로직 or 돌파로직
                #     logger.info('>>hadown_trend and hadown_longtrend Long -> Short : trend changed')
                #     # 돌파로직
                #     if hadown_fast and hadown_middle and hadown_slow:  # 모두 숏이면
                #         self.exchange.order('ChBrkShort', False, qty*2)
                #         self.exchange.cancel_all()
                #     else:
                #         self.exchange.close_all()
                # else:
                #     logger.info('>>StopLong')
                #     if price < fb100:  # 초과익절 로직
                #         self.exchange.order('StopLong1', False, qty, limit=fb100, post_only=True)
                #         # self.exchange.order('StopLong2', False, qty, limit=fb62, post_only=True)

            elif bitmex.get_whichpositon() == 'SHORT':
                logger.info('---------------------->>SHORT order status')
                logger.info('ordered price:%s' % bitmex.get_position_avg_price())
                if fast_rsi[-1] <= 5:  # 스탑로직
                    logger.info('>>fast_rsi[-1] <= 5')
                    self.exchange.order('StopShort', True, qty, limit=price - 0.5, post_only=True)
                elif haup_slow and haup_trend:  # 손절로직
                    logger.info('>>haup_trend and haup_longtrend Short -> Long : slow trend changed')
                    self.exchange.close_all()
                    self.exchange.cancel_all()

                # elif haup_trend and haup_longtrend:    # 손절로직 or 돌파로직
                #     logger.info('>>haup_trend and haup_longtrend Short -> Long :  trend changed')
                #     # 돌파로직
                #     if haup_fast and haup_middle and haup_slow:  # 모두 롱이면
                #         self.exchange.order('ChBrkLong', True, qty*2)
                #         self.exchange.cancel_all()
                #     else:
                #         self.exchange.close_all()
                # else:
                #     logger.info('>>StopShort')
                #     if price > fb0:  # 초과익절로직
                #         self.exchange.order('StopShort1', False, qty, limit=fb0, post_only=True)
                #         # self.exchange.order('StopShort2', False, qty, limit=fb38, post_only=True)
                #     logger.info('>>StopShort')

            else:
                logger.info('else: %s ' % bitmex.get_whichpositon())
                if haup_trend and haup_longtrend:
                    logger.info('+++++++++++ LLLLLLong Trend +++++++++++++++')
                    if bitmex.get_open_order('LCatch') is not None:  # catch shooting logic
                        logger.info('There are LongOver orders , now changed trend, and cancel all')
                        self.exchange.cancel_all()
                    self.exchange.order('SCatch', True, lot, limit=fb0, post_only=True)
                elif hadown_trend and hadown_longtrend:
                    logger.info('- - - - - - SSSSSSort Trend - - - - - - -')

                    if bitmex.get_open_order('SCatch') is not None:  # catch shooting logic
                        logger.info('There are ShortOver orders , now changed trend, and cancel all')
                        self.exchange.cancel_all()
                    self.exchange.order('LCatch', False, lot, limit=fb100, post_only=True)

                # if bitmex.get_open_order('LCatch') is not None and haup_trend:
                #     bitmex.cancel('LCatch')
                #
                # if bitmex.get_open_order('SCatch') is not None and hadown_trend:
                #     bitmex.cancel('SCatch')

                if haup_slow and haup_trend and haup_longtrend and fast_rsi[-1] <= 5:  # entry long condition on Short Trend
                    logger.info('Now Short conditions: fast_rsi[-1] <= 5 0k -->  %s' % fast_rsi[-1])
                    self.exchange.order('Long', True, lot, limit=price - 0.5, post_only=True)
                elif hadown_slow and hadown_trend and hadown_longtrend and fast_rsi[-1] >= 95:  # # entry short condition on Long Trend
                    logger.info('Now Long conditions: fast_rsi[-1] >= 95 0k -->  %s' % fast_rsi[-1])
                    self.exchange.order('Short', False, lot, limit=price + 0.5, post_only=True)

                if (slow_willr[-1] < -30) and haup_fast and haup_middle and haup_slow and haup_trend and haup_longtrend and haup_longlongtrend:
                    logger.info('in for H5UP')
                    self.stratey_mode = 'H5UP'
                    self.exchange.order('H5UP', True, lot)
                    bitmex.cancel_all()
                elif (slow_willr[-1] > -70) and hadown_fast and hadown_middle and hadown_slow and hadown_trend and hadown_longtrend and hadown_longtrend:
                    logger.info('in for H5DOWN')
                    self.stratey_mode = 'H5DOWN'
                    self.exchange.order('H5DOWN', False, lot)
                    bitmex.cancel_all()

        elif self.stratey_mode == 'H5UP':
            logger.info('=============== stratey_mode = H5UP ==============')

            if bitmex.get_whichpositon() != 'LONG' and (slow_willr[-1] < -30) and haup_fast and haup_middle and haup_slow and haup_trend and haup_longtrend and haup_longlongtrend:
                self.exchange.order('H5UP', True, lot)
            elif bitmex.get_whichpositon() != 'LONG' and not haup_fast and not haup_middle:
                # back to R2 mode
                self.stratey_mode = 'R2'
                bitmex.cancel_all()
            elif bitmex.get_whichpositon() == 'LONG' and (slow_willr[-1] > -11) or (haup_fast and not haup_middle and not haup_slow and not haup_longtrend):
                # stop order and back to R2 mode
                self.exchange.order('H5UPStop', False, lot)
                self.stratey_mode = 'R2'
                bitmex.cancel_all()

        elif self.stratey_mode == 'H5DOWN':
            logger.info('=============== stratey_mode = H5DOWN ==============')

            if bitmex.get_whichpositon() != 'SHORT' and (slow_willr[-1] > -70) and (hadown_fast and hadown_middle and hadown_slow and hadown_trend and hadown_longtrend and hadown_longlongtrend):
                self.exchange.order('H5DOWN', False, lot)
            elif bitmex.get_whichpositon() != 'SHORT' and not hadown_fast and not hadown_middle:
                # back to R2 mode
                self.stratey_mode = 'R2'
                bitmex.cancel_all()
            elif bitmex.get_whichpositon() == 'SHORT' and (slow_willr[-1] < -91) or (not hadown_fast and not hadown_middle and not hadown_slow and not hadown_longtrend):  # and not hadown_slow):   #(fast_slow_rsi <= 93) or
                # stop order and back to R2 mode
                self.exchange.order('H5DOWNStop', True, lot)
                self.stratey_mode = 'R2'
                bitmex.cancel_all()
        else:
            logger.info('=============== stratey_mode = Else ==============')

            # back to R2 mode
            self.stratey_mode = 'R2'
            bitmex.cancel_all()

        if flg_changed_timezone is True:
            self.idx += 1

        # save pre-timezone's fb0, fb100 values
        self.pre_fb0 = fb0
        self.pre_fb100 = fb100

        diff = (abs(bitmex.get_balance() - abs(self.prebalance)))
        realised_pnl = bitmex.get_margin()['realisedPnl']
        logger.info('prebalance():%s' % self.prebalance)
        logger.info('bitmex.get_balance():%s' % bitmex.get_balance())
        logger.info('diff:%s' % diff)
        logger.info('realised_pnl:%s' % realised_pnl)

        logger.info('-------------------------strategy end-----------------------\n')