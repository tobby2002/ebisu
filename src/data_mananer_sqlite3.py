# coding: UTF-8

import os
import time
import pandas as pd
import sqlite3
from datetime import timedelta, datetime, timezone
from src import allowed_range, retry, delta, load_data, resample
from src.bitmex import BitMex
from src.bitmex_stub import BitMexStub
from src.bitmex_backtest import BitMexBackTest


OHLC_DIRNAME = os.path.join(os.path.dirname(__file__), "./data/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "./data/{}/data.csv")

def get_conn():
    dbpath = "data_bitmex.sqlite"
    conn = sqlite3.connect(dbpath)
    return conn

def create_newtable(conn, tablename):
    cur = conn.cursor()
    '''
    timestamp,open,high,low,close,volume
    2019-03-23 07:53:00+00:00,3995.0,3994.5,3992.5,3992.5,415222
    2019-03-23 07:54:00+00:00,3992.5,3993.0,3992.5,3993.0,82759
    2019-03-23 07:55:00+00:00,3993.0,3993.0,3989.5,3990.0,2429478
    2019-03-23 07:56:00+00:00,3990.0,3990.0,3988.5,3989.0,866484
    
    '''
    cur.executescript("""
    /* 테이블이 이미 있다면 제거하기 */
    /* DROP TABLE IF EXISTS bitmex_1m;*/
    
    /* 테이블 생성하기 */
    CREATE TABLE %s(
        timestamp TEXT,
        open NUMERIC,
        high NUMERIC,
        low NUMERIC,
        close NUMERIC,
        volume NUMERIC
    );
    
    /* 데이터 넣기 */
    INSERT INTO bitmex_1m(timestamp,open,high,low,close,volume)VALUES('2019-03-23 07:53:00+00:00',3995.0,3994.5,3992.5,3992.5,415222);
    INSERT INTO bitmex_1m(timestamp,open,high,low,close,volume)VALUES('2019-03-23 07:54:00+00:00',3992.5,3993.0,3992.5,3993.0,82759);
    INSERT INTO bitmex_1m(timestamp,open,high,low,close,volume)VALUES('2019-03-23 07:53:00+00:00',3995.0,3994.5,3992.5,3992.5,415222);
    """ % tablename)
    # 위의 조작을 데이터베이스에 반영하기 --- (※3)
    conn.commit()
    conn.close()


def drop_table(conn, tablename):
    cur = conn.cursor()
    cur.executescript("""
    /* 테이블이 이미 있다면 제거하기 */
    DROP TABLE IF EXISTS bitmex_1m;
    """ % tablename)
    # 위의 조작을 데이터베이스에 반영하기 --- (※3)
    conn.commit()
    conn.close()

def show_table(conn, tablename):
    cur = conn.cursor()
    # cur.execute("SELECT timestamp,open,high,low,close,volume FROM %s" % tablename)
    cur.execute("SELECT * FROM %s" % tablename)
    item_list = cur.fetchall()
    print('%s table, %s 건' % (tablename, len(item_list)))
    # print('------------')
    for it in item_list:
        print(it)
    # print('------------')
    print('%s table, %s 건' % (tablename, len(item_list)))


def test_fetch_ohlcv_1m(mins):
    '''
    source => DataFrame Type
    ------------------------------------------------------------------
                               open    high     low   close   volume
    2019-06-15 14:29:00+00:00  8669.5  8670.0  8667.0  8667.0  1454667
    2019-06-15 14:30:00+00:00  8667.0  8667.5  8667.0  8667.5   424940
    :return:
    '''
    bitmex = BitMex(threading=False)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - 1 * timedelta(minutes=mins)
    source = bitmex.fetch_ohlcv('1m', start_time, end_time)
    return source

def load_df(conn, table):
    cur = conn.cursor()
    query = cur.execute("SELECT * From %s" % table)
    cols = [column[0] for column in query.description]
    query_df = pd.DataFrame.from_records(data=query.fetchall(), columns=cols)
    conn.close()
    return query_df



if __name__ == "__main__":
    '''
    # https://docs.python.org/ko/3/library/sqlite3.html
    # https://wikidocs.net/5332
    # https://tariat.tistory.com/9
    '''
    conn = get_conn()
    # create_newtable(conn, 'bitmex_1m')  # drop and create new table by tablename
    # show_table(conn, 'bitmex_1m')  # show table content

    # print('download data from server')
    # start = time.time()  # 시작 시간 저장
    # source = test_fetch_ohlcv_1m(10000)  # 1min 짜리 1000건
    # print('download_data time:', time.time() - start)
    #
    # start = time.time()  # 시작 시간 저장
    # source.to_sql('bitmex_1m', conn, if_exists='replace')
    # # source.to_sql('bitmex_1m_01', conn, if_exists='append')
    # print('save_data time:', time.time() - start)

    show_table(conn, 'bitmex_1m')  # show table content

    # start = time.time()  # 시작 시간 저장
    # data_1m = load_df(conn, 'bitmex_1m')
    # print('load_data time:', time.time() - start)
    #
    # print(data_1m)













