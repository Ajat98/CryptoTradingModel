#ALL IMPORTS
from EvaluateStrategy import EvaluateStrategy
from Strategies import *

from Binance import Binance
from TradeModel import TradeModel

import json
from decimal import Decimal, getcontext

#Backtest all strategies over symbols of choice
#Updated in v4, make easier to customize
def BackTestStrategies(
    symbols=[], interval = '4h', plot=False, strategy_evaluators=[],
    options = dict(starting_balance = 100, initial_profits = 1.01, initial_stop_loss = 0.9,
    incremental_profits = 1.006, incremental_stop_loss = 0.996)):

    tested_coins = 0
    trade_value = options['starting_balance']

    for symbol in symbols:
        print(symbol)
        model = TradeModel(symbol=symbol, timeframe=interval)

        for evaluator in strategy_evaluators:
            resulting_balance = evaluator.backtest(
                model,
                starting_balance= options['starting_balance'],
                initial_profits = options['initial_profits'],
                initial_stop_loss = options['initial_stop_loss'],
                incremental_profits = options['incremental_profits'],
                incremental_stop_loss = options['incremental_stop_loss']
                )
            
            if resulting_balance != trade_value:
                print(evaluator.strategy.__name__
                + ': starting balance: ' + str(trade_value)
                + ': resulting balance: ' + str(round(resulting_balance, 2)))

                if plot:
                    model.plot_data(
                        buy_signals = evaluator.results[model.symbol]['buy_times'],
                        sell_signals = evaluator.results[model.symbol]['sell_times'],
                        plot_title = evaluator.strategy.__name__ + ' with ' + model.symbol)

                evaluator.profits_list.append(resulting_balance - trade_value)
                evaluator.updateResult(trade_value, resulting_balance)

            tested_coins = tested_coins + 1
    
    for evaluator in strategy_evaluators:
        print("")
        evaluator.printResult()

    
#Message user will see on matched symbol:
strat_matched_symbol = "\n Strategy Found a Match! \
    \n To backtest the strategy and see a plot, press 'b' then ENTER \
    \n To Place an order, press 'p' Then Enter \
    \n Press anything else to skip placing an order" 

prompt_place_order = "/nPress 'p' then ENTER to place an order \
    \n press anything else or ENTER to skip placing an order"

#Check current markets, option to place order if strategy conditions are met
def evalStrategies(symbols = [], strategy_evaluators = [], interval = '1h',
options = dict(starting_balance = 100, initial_profits = 1.012, initial_stop_loss = 0.9,
incremental_profits = 1.006, incremental_stop_loss = 0.996)):
    for symbol in symbols:
        print(symbol)
        model = TradeModel(symbol=symbol, timeframe=interval)
        for evaluator in strategy_evaluators:
            if evaluator.evaluate(model):
                print('\n' + evaluator.strategy.__name__ + " match on " + symbol)
                print(strat_matched_symbol)
                answer = input()

                if answer == 'b':
                    resulting_balance = evaluator.backtest(
                        model,
                        starting_balance= options['starting_balance'],
                        initial_profits = options['initial_profits'],
                        initial_stop_loss = options['initial_stop_loss'],
                        incremental_profits = options['incremental_profits'],
                        incremental_stop_loss = options['incremental_stop_loss']
                    )
                    model.plot_data(
                        buy_signals = evaluator.results[model.symbol]['buy_times'],
                        sell_signals = evaluator.results[model.symbol]['sell_times'],
                        plot_title = evaluator.strategy.__name__ + 'match on ' + symbol
                    )
                    print(evaluator.results[model.symbol])
                    print(prompt_place_order)
                    answer = input()

                if answer == 'p':
                    print('\n Placing buy order now')
                    #Need to update makeOrder func, since it will not know what symbol to buy beforehand
                    #Binance only allows min orders sizes above a certain amount, need to make sure we always buy
                    #Above that amount, depending on price of the quote asset
                    order_result = model.exchange.makeOrder(model.symbol, "BUY", "MARKET", quantity=0.02, test=False)
                    if 'code' in order_result:
                        print("\n Error.")
                        print(order_result)
                    else:
                        print('\n Sucessful order.')
                        print(order_result)

starting_message = "Crypto Trading Bot. \n \
    Press 'b' then ENTER to backtest all strategies \n \
    Press 'e' then ENTER to execute all strategies on all trading pairs. \n \
    Press 'q' then ENTER to exit program. "

def Main():
    exchange = Binance()
    symbols = exchange.getTradeSymbols(quoteAssets=['ETH'])

    strategy_evaluators = [
        #EvaluateStrategy(strategy_function=Strategies.bollStrategy),
        #EvaluateStrategy(strategy_function=Strategies.maStrategy),
        #EvaluateStrategy(strategy_function=Strategies.ichimokuBull)
        EvaluateStrategy(strategy_function=strategies_dict['ma_crossover'])
    ]
    
    print(starting_message)
    
    answer = input()
    while answer not in ['b', 'q', 'e']:
        print(starting_message)
        answer = input()
    if answer == 'e':
        evalStrategies(symbols=symbols, interval='1h', strategy_evaluators=strategy_evaluators)
    if answer == 'b':
        #Change plot=True to make graphs of each symbol to trade
        BackTestStrategies(symbols=symbols, interval='1h', plot=False, strategy_evaluators=strategy_evaluators)
    if answer == 'q':
        print('\nExiting now...\n')

    

if __name__ == '__main__':
    Main()
