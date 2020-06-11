import pandas as  pd 
from decimal import Decimal, getcontext

class EvaluateStrategy:
    """Evaluate performance of diff strategies through simple backtest"""

    def __init__(self, strategy_function, strategy_settings:dict = {'indicators':['low_boll', 'short_sma', 'long_sma']}):

        self.strategy = strategy_function
        self.settings = strategy_settings
        self.buy_times = []
        self.sell_times = []

        self.profitable_symbols = 0
        self.unprofitable_symbols = 0

        self.complete_starting_balance = 0
        self.complete_resulting_balance = 0

        self.profits_list = []
        self.results = dict()

    def backtest(self,
    model,
    starting_balance:float=100,
    initial_profits:float = 1.045,
    initial_stop_loss:float = 0.85,
    incremental_profits:float = 1.04,
    incremental_stop_loss:float = 0.975):
        
        #Function to backtest strategy and set rules
        #Will return balance that could have been a result of running the current strategy

        #Error checking
        if initial_stop_loss >= 1 or initial_stop_loss <= 0:
            AssertionError('initial_stop_loss should be greater than 0 and less than 1')

        if initial_profits <= 1:
            AssertionError('initial_profits must be greater than 1')
        
        df = model.df 
        buy_times, sell_times = [], []

        last_buy = None

        #Calculations to 30th decimal for accuracy
        getcontext().prec = 30

        resulting_balance = Decimal(starting_balance)
        stop_loss = Decimal(initial_stop_loss)
        profit_target = Decimal(initial_profits)
        buy_price = 0

        #iterate through all candlesticks
        #Check if strategy is fulfilled and if it is a buy or sell time. Only checks sell if previously bought the symbol
        for i in range(len(df['close'])-1):
            #Check if bought
            if last_buy is None:
                #Check if strategy is fulfilled
                strategy_result = self.strategy(model.df, i)

                if strategy_result:
                    #If strat is fulfilled, buy the symbol/coin, set stop loss and take profit
                    buy_price = Decimal(strategy_result)
                    last_buy = {
                        'index':i,
                        'price': buy_price
                    }

                    buy_times.append([df['time'][i], buy_price])

                    stop_loss = Decimal(initial_stop_loss)
                    profit_target = Decimal(initial_profits)
            
            #If already bought, checkc if price has hit SL or TP
            elif last_buy is not None and i > last_buy['index'] + 1:
                stop_loss_price = last_buy['price'] * stop_loss
                next_target_price = last_buy['price'] * profit_target

                #if price goes below SL, sell at that price
                if df['low'][i] < stop_loss_price:
                    sell_times.append([df['time'][i], stop_loss_price])
                    resulting_balance = resulting_balance * (stop_loss_price / buy_price)

                    #reset values for last_buy
                    last_buy = None
                    buy_price = Decimal(0)

                elif df['high'][i] > next_target_price:
                    #if price goes above target, increase SL and adjust next target.
                    last_buy = {
                        'index': i,
                        'price': Decimal(next_target_price),
                    }

                    stop_loss = Decimal(incremental_stop_loss)
                    profit_target = Decimal(incremental_profits)
        
        #Aggregate results, add to the model's symbol
        self.results[model.symbol] = dict(
            returns = round(Decimal(100.0) * (resulting_balance / Decimal(starting_balance) - Decimal(1.0)), 3),
            buy_times = buy_times,
            sell_times = sell_times
        )

        if resulting_balance > starting_balance:
            self.profitable_symbols = self.profitable_symbols + 1
        elif resulting_balance < starting_balance:
            self.unprofitable_symbols = self.unprofitable_symbols + 1

        return resulting_balance

        #Check only last candlestick for strategy fullfilment
    def evaluate(self, model):
        last_entry = len(model.df['close']) -1
        return self.strategy(model.df, last_entry)

        #Helper functions
    def updateResult(self, starting_balance, resulting_balance):
        self.complete_starting_balance = self.complete_starting_balance + starting_balance
        self.complete_resulting_balance = self.complete_resulting_balance + resulting_balance

    def printResult(self):
        print(self.strategy.__name__+' STATS ')
        print('Profitable Symbols: ' + str(self.profitable_symbols))
        print('Unprofitable Symbols: ' + str(self.unprofitable_symbols))

        if len(self.profits_list) > 0:
            profitability = Decimal(100.0) * (self.complete_resulting_balance/self.complete_starting_balance - Decimal(1.0))

            print('Total Profit: ' + str(round(sum(self.profits_list), 3)))
            print('Least Profitable Trade: ' + str(round(min(self.profits_list),3)))
            print('Most Profitable Trade: ' + str(round(max(self.profits_list), 3)))
            print('Initial balance was ' + str(self.complete_starting_balance) +\
            ' and the final balance is ' + str(round(self.complete_resulting_balance, 3)))
            print('Overall profitability is ' +str(round(profitability, 3)) + '%')



            










