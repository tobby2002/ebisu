# coding: UTF-8

import unittest
from datetime import datetime, timezone, timedelta

from src import delta, allowed_range
from src.bitmex import BitMex


class TestBitMex(unittest.TestCase):

    # def test_fetch_ohlcv_5m(self):
    #     bitmex = BitMex(threading=False)
    #     end_time = datetime.now(timezone.utc)
    #     start_time = end_time - 5 * timedelta(minutes=5)
    #     source = bitmex.fetch_ohlcv('5m', start_time, end_time)
    #     assert len(source) > 1
    #
    # def test_fetch_ohlc_2h(self):
    #     bitmex = BitMex(threading=False)
    #     end_time = datetime.now(timezone.utc)
    #     start_time = end_time - 5 * timedelta(hours=2)
    #     source = bitmex.fetch_ohlcv('2h', start_time, end_time)
    #     assert len(source) > 1
    #
    # def test_fetch_ohlcv_11m(self):
    #     ohlcv_len = 100
    #     bin_size = '11m'
    #     bitmex = BitMex(threading=False)
    #
    #     end_time = datetime.now(timezone.utc)
    #     start_time = end_time - ohlcv_len * delta(bin_size)
    #     d1 = bitmex.fetch_ohlcv(bin_size, start_time, end_time)
    #     print(f"{d1}")

    def test_entry_cancel(self):
        bitmex = BitMex()
        bitmex.demo = False

        # 전처리 모든 포지션 시장가 해제
        # bitmex.close_all()
        price = bitmex.get_market_price()

        id = "Long"
        # bitmex.entry(id, True, 1, limit=price)

        get_position_size= bitmex.get_position_size()
        print('get_position_size: %s' % get_position_size)

        get_position_avg_price= bitmex.get_position_avg_price()
        print('get_position_avg_price: %s' % get_position_avg_price)


        get_position= bitmex.get_position()
        print('get_position: %s' % get_position)

        get_margin= bitmex.get_margin()
        print('get_margin: %s' % get_margin)

        # bitmex.get_open_order(id)
        # print('bitmex.get_open_order(id):%s' % bitmex.get_open_order(id))

        # 注文、キャンセルの試験
        # id = "Long"
        # bitmex.entry(id, True, 1, limit=price-1000)
        # assert bitmex.get_open_order(id) is not None
        # bitmex.cancel(id)
        # assert bitmex.get_open_order(id) is None



        # # 注文の更新
        # id = "Long"
        # bitmex.entry(id, True, 1, limit=price-1000)
        # order = bitmex.get_open_order(id)
        # assert order["orderQty"] == 1
        # assert order["price"] == price-1000
        # bitmex.entry(id, True, 2, limit=price-900)
        # order = bitmex.get_open_order(id)
        # assert order["orderQty"] == 2
        # assert order["price"] == price-900
        # bitmex.cancel(id)
        # assert bitmex.get_open_order(id) is None

