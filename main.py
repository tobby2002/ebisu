#!/usr/bin/env python
# coding: UTF-8

import argparse
import signal
import time

from src.factory import BotFactory

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This is trading script on bitmex")
    parser.add_argument("--test",     default=False,   action="store_true")
    parser.add_argument("--stub",     default=False,   action="store_true")
    parser.add_argument("--demo",     default=False,   action="store_true")
    parser.add_argument("--hyperopt", default=False,   action="store_true")
    parser.add_argument("--strategy", default="doten", required=True)
    args = parser.parse_args()

    # 봇을 생성
    bot = BotFactory.create(args)
    # 봇을 실행
    bot.run()

    if not args.test:
        # 정지처리등록
        signal.signal(signal.SIGINT, lambda x, y: bot.stop())
        while True:
            time.sleep(1)
