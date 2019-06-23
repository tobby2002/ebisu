# coding: UTF-8

import os
import time
import pandas as pd
import sqlite3
import threading

from sqlite3 import Error
from datetime import timedelta, datetime, timezone
from src import allowed_range, retry, delta, load_data, resample
from src.bitmex import BitMex

OHLC_DIRNAME = os.path.join(os.path.dirname(__file__), "./data/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "./data/{}/data.csv")

'''
http://www.sqlitetutorial.net/sqlite-python/sqlite-python-select/
'''
def get_conn():
    dbpath = "data_bitmex.sqlite"
    try:
        conn = sqlite3.connect(dbpath)
        return conn
    except Error as e:
        print(e)
    return None

def create_newtable(conn, table, bin_size):
    cur = conn.cursor()
    '''
    timestamp,open,high,low,close,volume
    2019-03-23 07:53:00+00:00,3995.0,3994.5,3992.5,3992.5,415222
    2019-03-23 07:54:00+00:00,3992.5,3993.0,3992.5,3993.0,82759
    2019-03-23 07:55:00+00:00,3993.0,3993.0,3989.5,3990.0,2429478
    2019-03-23 07:56:00+00:00,3990.0,3990.0,3988.5,3989.0,866484
    
    CREATE TABLE %s(
        timestamp TEXT,
        open NUMERIC,
        high NUMERIC,
        low NUMERIC,
        close NUMERIC,
        volume NUMERIC
    );
    
    /* 데이터 넣기 */
    # INSERT INTO bitmex_1m(timestamp,open,high,low,close,volume)VALUES('2019-03-23 07:53:00+00:00',3995.0,3994.5,3992.5,3992.5,415222);
    # INSERT INTO bitmex_1m(timestamp,open,high,low,close,volume)VALUES('2019-03-23 07:54:00+00:00',3992.5,3993.0,3992.5,3993.0,82759);
    # INSERT INTO bitmex_1m(timestamp,open,high,low,close,volume)VALUES('2019-03-23 07:53:00+00:00',3995.0,3994.5,3992.5,3992.5,415222);
    
    '''
    cur.executescript("""
    /* 테이블이 이미 있다면 제거하기 */
    /* DROP TABLE IF EXISTS bitmex_1m;*/
    /* 테이블 생성하기 */

    CREATE TABLE %s_%s(
        timestamp TIMESTAMP,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER
    );
    """ % (table, bin_size))
    print('create_table : %s_%s' % (table, bin_size))
    conn.commit()
    conn.close()


def drop_table(conn, table, bin_size):
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS %s_%s;
    """ % (table, bin_size))
    conn.commit()
    conn.close()
    print('drop_table : %s_%s' % (table, bin_size))

def truncate_table(conn, table, bin_size):
    cur = conn.cursor()
    cur.executescript("""
    DELETE FROM %s_%s;
    VACUUM;
    """ % (table, bin_size))
    conn.commit()
    conn.close()
    print('truncate_table : %s_%s' % (table, bin_size))

def show_table(conn, table, bin_size, limit):
    cur = conn.cursor()
    if limit > 0:
        sql = str("select ROWID, * from '%s_%s' order by ROWID desc limit %d" % (table, bin_size, limit))
        cur.execute(sql)
        item_list = cur.fetchall()
    else:
        cur.execute("SELECT ROWID, * FROM %s_%s" % (table, bin_size))
        item_list = cur.fetchall()

    for it in item_list:
        print(it)
    print('%s_%s table, %s 건' % (table, bin_size, len(item_list)))

def test_fetch_ohlcv_1m(mins):
    '''
    source => DataFrame Type
    ------------------------------------------------------------------
                               open    high     low   close   volume
    2019-06-15 14:29:00+00:00  8669.5  8670.0  8667.0  8667.0  1454667
    2019-06-15 14:30:00+00:00  8667.0  8667.5  8667.0  8667.5   424940
    :return:
    '''
    # bitmex = BitMex(threading=False)
    bitmex = BitMex(threading=True)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - 1 * timedelta(minutes=mins)
    source = bitmex.fetch_ohlcv('1m', start_time, end_time)
    return source

'''
    # download and save to database
    # conn = get_conn()
    # df = download_df_ohlcv('1m', 129600, threading=True)  # 1m, 1000건, 현재까지 e.g. 60*24=1440 -> 1D -> (1440*30)=43200 1MONTH, 129600 3MONTH,
    # save_to_db(conn, df, 'bitmex_1m', 'replace')
    # show_table(conn, 'bitmex_1m')  # show table content
'''
def download_df_ohlcv(bin_size, ohlcv_len, **kwargs):
    '''
    df => DataFrame Type
    ------------------------------------------------------------------
                               open    high     low   close   volume
    2019-06-15 14:29:00+00:00  8669.5  8670.0  8667.0  8667.0  1454667
    2019-06-15 14:30:00+00:00  8667.0  8667.5  8667.0  8667.5   424940
    :return:
    '''
    print('download data from server')
    start = time.time()
    # bitmex = BitMex(threading=False)
    bitmex = BitMex(threading=True)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - ohlcv_len * delta(bin_size)
    df = bitmex.fetch_ohlcv(bin_size, start_time, end_time)
    print('download_df_ohlcv time:', time.time() - start)
    return df

def save_to_db(conn, df, tablename, replace):  # if_exists='replace' or if_exists='append'
    # start = time.time()
    df.to_sql(tablename, conn, if_exists=replace)
    # print('save_data time:', time.time() - start)

def load_df(conn, table, bin_size):
    cur = conn.cursor()
    query = cur.execute("SELECT * From %s_%s" % (table, bin_size))
    cols = [column[0] for column in query.description]
    query_df = pd.DataFrame.from_records(data=query.fetchall(), columns=cols)
    return query_df

def download_save_show_by_1m(conn, table, bin_size, ohlcv_len):
    print('download data from server')
    start = time.time()
    source = test_fetch_ohlcv_1m(ohlcv_len)  # 1min 짜리 1000건
    print('download_data time:', time.time() - start)

    start = time.time()
    source.to_sql('bitmex_1m', conn, if_exists='replace')
    print('save_data time:', time.time() - start)
    show_table(conn, table, ohlcv_len, 10)

def autorelay_download_save(conn, table, bin_size, ohlcv_len, append):
    cur = conn.cursor()
    startd = time.time()
    bitmex = BitMex(threading=True)
    sql = str("select ROWID, * from '%s_%s' order by ROWID desc limit 1" % (table, bin_size))
    cur.execute(sql)
    item_list = cur.fetchall()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - ohlcv_len * delta(bin_size)

    # 데이터가 있으면 릴레이 다운로드 자동으로 기간설정
    if item_list:
        lasttime = item_list[0][1]
        # print(lasttime)
        # print(lasttime[0:16])
        last_time = datetime.strptime(lasttime[0:16], '%Y-%m-%d %H:%M')
        start_time = last_time + timedelta(minutes=1)
    else:
        # 데이터가 없으면,
        print('No data and will start from ', start_time)
        pass

    # print('start_time:', start_time)
    # print('end_time:', end_time)

    # relay download 디폴트 기간 설정만큼 다운로드 한다.
    df = bitmex.fetch_ohlcv(bin_size, start_time, end_time)
    print('download_df_ohlcv time: ', time.time() - startd)

    # insert to database
    df.to_sql(table+'_'+bin_size, conn, if_exists=append)
    show_table(conn, table, bin_size, 1)

def run_downloader_by_thread():
    print('=====', time.ctime(), '== run downloader by thread ===')
    try:
        conn = get_conn()
        autorelay_download_save(conn, 'bitmex', '1m', 1000, 'append')
        conn.commit()
        conn.close()
    except Exception as e:  # 에러 종류
        print('In run_downloader_by_thread : ex, ', e)
    threading.Timer(1, run_downloader_by_thread).start()

if __name__ == "__main__":
    '''
    # https://docs.python.org/ko/3/library/sqlite3.html
    # https://wikidocs.net/5332
    # https://tariat.tistory.com/9
    '''

    '''
    # drop table
    '''
    # conn = get_conn()
    # drop_table(conn, 'bitmex, '1m')

    '''
    # create table
    '''
    # conn = get_conn()
    # create_newtable(conn, 'bitmex', '1m')  # drop and create new table by tablename
    '''
    # truncate table
    '''
    # conn = get_conn()
    # truncate_table(conn, 'bitmex', '1m')

    '''
    # show table
    '''
    # conn = get_conn()
    # show_table(conn, 'bitmex', '1m', 10)  # 0 --> all list

    '''
    # download and save to database and show data
    '''
    # conn = get_conn()
    # periods = 10
    # df = download_df_ohlcv('1m', periods, threading=True)  # 1m, periods:1440건, 현재까지 e.g. 60*24=1440 -> 1D / (1440*30)=43200 1MONTH / 129600 3MONTH,
    # save_to_db(conn, df, 'bitmex_1m', 'replace')
    # show_table(conn, 'bitmex, '1m', 10)

    '''
    # auto relay download & save to database and show data
    '''
    # autorelay_download_save(get_conn(), 'bitmex', '1m', 5, 'append')

    '''
    # By Thread, auto relay download & save to database and show data
    '''
    run_downloader_by_thread()














