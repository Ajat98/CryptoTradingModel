#ALL IMPORTS
from EvaluateStrategy import EvaluateStrategy
from Strategies import Strategies

from Binance import Binance
from TradeModel import TradeModel

import json
from decimal import Decimal, getcontext

#Backtest all strategies over symbols of choice
def BackTestStrategies(symbols=[], interval = '4h', plot=False):
    trade_value = 100
    strategy_evaluators = [
        EvaluateStrategy( strategy_function=Strategies.bollStrategy, strategy_settings={'indicators':['low_boll']}),
        EvaluateStrategy( strategy_function=Strategies.maStrategy, strategy_settings={'indicators':['short_sma']})
    ]

    tested_coins = 0

    for symbol in symbols:
        print(symbol)
        model = TradeModel(symbol=symbol, timeframe=interval)

        for evaluator in strategy_evaluators:
            resulting_balance = evaluator.backtest(
                model,
                starting_balance= trade_value,
                )
            
            if resulting_balance != trade_value:
                print(evaluator.strategy.__name__
                + ': starting balance: ' + str(trade_value)
                + ': resulting balance: ' + str(round(resulting_balance, 2)))

            if plot:
                model.plot_data(
                    buy_signals = evaluator.results[model.symbol]['buy_times'],
                    sell_signals = evaluator.results[model.symbol]['sell_times'],
                    plot_title = evaluator.strategy.__name__ + ' with ' + model.symbol,
                    indicators = evaluator.settings['indicators'])

            evaluator.profits_list.append(resulting_balance - trade_value)
            evaluator.updateResult(trade_value, resulting_balance)

        tested_coins = tested_coins + 1
    
    for evaluator in strategy_evaluators:
        print("")
        evaluator.printResult()


def Main():
    exchange = Binance()
    symbols = exchange.get_trade_symbols(quoteAssets=['USDT'])

    BackTestStrategies(symbols=symbols, interval='1h', plot=True)

if __name__ == '__main__':
    Main()


                

