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
        # lot = int(round(lot / 50))
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
        slow_len = self.input('slow_len', int, 70)

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
        if super2_long: # and rsi50_over: # rsi2_overbought and price_under:  # long entry condtions
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

        if super2_short:  # and rsi50_under:  # short trend
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
        # lot = int(round(lot / 50))
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
        half_len = self.input('fast_len', int, 50)
        slow_len = self.input('slow_len', int, 70)

        fast_sma = sma(close, fast_len)
        half_sma = sma(close, half_len)
        slow_sma = sma(close, slow_len)

        # conditions
        sma_long = over(fast_sma[-1], slow_sma[-1])
        sma_short = under(fast_sma[-1], slow_sma[-1])

        super_long = over(close[-1], supertrenddf['TSL'][-1])
        super_short = under(close[-1], supertrenddf['TSL'][-1])
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
        if super_long: # and rsi50_over: # rsi2_overbought and price_under:  # long entry condtions
            logger.info('+ + + + + LONG + + + + + LONG + + + + + LONG + + + + + ')
            if bitmex.get_whichpositon() is None and (rsi2_oversold or price_under):
                logger.info('postion condition > None')
                self.exchange.entry("Long", True, lot, limit=price-0.5, post_only=True)

            elif bitmex.get_whichpositon() == 'LONG':
                logger.info('postion condition  > LONG')
                if rsi2_oversold: # closing
                    logger.info('postion condition  > LONG > Closing')
                    self.exchange.order("Long", False, abs(bitmex.get_position_size()), limit=price - 0.5, when=price_over, post_only=True)
                elif rsi2_overbought: # add more entry
                    logger.info('postion condition  > LONG > Rsi2 overbout')
                    self.exchange.entry("LongAdd", True, lot, limit=price - 0.5, post_only=True)
                elif super_short: # stop loss
                    logger.info('postion condition  > LONG > super_short(stop loss)')
                    self.exchange.entry("Long", True, lot)
                    self.exchange.entry("LongAdd", True, lot)

            elif bitmex.get_whichpositon() == 'SHORT':
                logger.info('cancel SHORT on long trend')
                # self.exchange.cancel_all()
                self.exchange.close_all()
                self.exchange.close_all()
            else:

                logger.info('Super Shot --> Else')

        if super_short:  # and rsi50_under:  # short trend
            logger.info('- - - - - SHORT - - - - - SHORT - - - - - SHORT - - - - - ')
            if bitmex.get_whichpositon() is None and rsi2_overbought and price_over:
                logger.info('postion condition > None')
                self.exchange.entry("Short", False, lot, limit=price+0.5, post_only=True)

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

class Cross5M(Bot):
    def __init__(self):
        Bot.__init__(self, '5m')

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

        # logger.info("lot:"+str(lot))
        # logger.info("data:"+str(self.exchange.data))
        # logger.info("fast_sma:"+str(fast_sma))
        # logger.info("slow_sma:"+str(slow_sma))

        if golden_cross:
            self.exchange.entry("Long", True, lot)
            # logger.info(f"golden_cross trade : Long")
        if dead_cross:
            self.exchange.entry("Short", False, lot)
            # logger.info(f"dead_cross trade : Short")


class Cross1M(Bot):
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


# class SuperTrend1M(Bot):
#     variants = [sma, ema, double_ema, triple_ema, wma, ssma, hull]
#     eval_time = None
#
#     def __init__(self):
#         Bot.__init__(self, '1m')
#
#     def ohlcv_len(self):
#         return 15 * 30
#
#     def options(self):
#         return {
#             'variant_type': hp.quniform('variant_type', 0, len(self.variants) - 1, 1),
#             'basis_len': hp.quniform('basis_len', 1, 30, 1),
#             'resolution': hp.quniform('resolution', 1, 10, 1),
#             'sma_len': hp.quniform('sma_len', 1, 15, 1),
#             'div_threshold': hp.quniform('div_threshold', 1, 6, 0.1),
#         }
#
#     def strategy(self, open, close, high, low, volume):
#         lot = self.exchange.get_lot()
#
#         variant_type = self.input(defval=5, title="variant_type", type=int)
#         basis_len = self.input(defval=19,  title="basis_len", type=int)
#         resolution = self.input(defval=2, title="resolution", type=int)
#         sma_len = self.input(defval=9, title="sma_len", type=int)
#         div_threshold = self.input(defval=3.0, title="div_threshold", type=float)
#
#         source = self.exchange.security(str(resolution) + 'm')
#
#         print('source:'+str(source))
#         if self.eval_time is not None and self.eval_time == source.iloc[-1].name:
#             return
#
#         series_open = source['open'].values
#         series_close = source['close'].values
#
#         variant = self.variants[variant_type]
#
#         val_open = variant(series_open,  basis_len)
#         val_close = variant(series_close, basis_len)
#
#         if val_open[-1] > val_close[-1]:
#             high_val = val_open[-1]
#             low_val = val_close[-1]
#         else:
#             high_val = val_close[-1]
#             low_val = val_open[-1]
#
#         sma_val = sma(close, sma_len)
#
#         # self.exchange.plot('val_open', val_open[-1], 'b')
#         # self.exchange.plot('val_close', val_close[-1], 'r')
#         #
#         # self.exchange.entry("Long", True,   lot, stop=math.floor(low_val), when=(sma_val[-1] < low_val))
#         # self.exchange.entry("Short", False, lot, stop=math.ceil(high_val), when=(sma_val[-1] > high_val))
#
#         open_close_div = sma(numpy.abs(val_open - val_close), sma_len)
#
#         if open_close_div[-1] > div_threshold and \
#                 open_close_div[-2] > div_threshold < open_close_div[-2]:
#             self.exchange.close_all()
#
#         self.eval_time = source.iloc[-1].name
#
#         supertrend_multiplier1 = self.input('supertrend_multiplier1', int, 3)
#         supertrend_period1 = self.input('supertrend_period1', int, 14)
#         supertrend_multiplier2 = self.input('supertrend_multiplier2', int, 6)
#         supertrend_period2 = self.input('supertrend_period2', int, 28)
#
#         supertrend_df1 = supertrend(source, supertrend_period1, supertrend_multiplier1)  #.sort_index(axis=1,ascending=False)
#         print("111:"+supertrend_df1.head(10).to_string())
#         print("222:"+str(supertrend_df1['SuperTrend'].iloc[0]))
#
#         supertrend_df2 = supertrend(source, supertrend_period2, supertrend_multiplier2)
#         # print(supertrend_df1.tail(10).to_string())
#         # supertrend2 = supertrend_df2['SuperTrend']
#
#
#
#         long = (val_close[-1] < supertrend1 < supertrend2)
#         short = (val_close[-1] > supertrend1 > supertrend2)
#         close_all = val_close[-1] > supertrend1 and close < supertrend2
#
#         if long:
#             self.exchange.entry("Long:", True, lot)
#             logger.info("Long"+str(supertrend1))
#         elif short:
#             self.exchange.entry("Short", False, lot)
#             logger.info("short;"+str(supertrend1))
#         elif close_all:
#             self.exchange.close_all()
#             # logger.info("close_all;"+str(rci_s)+","+str(rci_m)+","+str(rci_l))