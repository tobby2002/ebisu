# coding: UTF-8

import src.strategy as strategy


class BotFactory():

    @staticmethod
    def create(args):
        """
        Bot 작성 함수, 이름(class 명)에서 해당 Bot을 src/strategy.py 에서 검색。
        :param args: 변수
        :return: Bot
        """
        try:
            cls = getattr(strategy, args.strategy)
            bot = cls()
            bot.test_net  = args.demo
            bot.back_test = args.test
            bot.stub_test = args.stub
            bot.hyperopt  = args.hyperopt
            return bot
        except Exception as _:
            raise Exception(f"Not Found Strategy : {args.strategy}")
