#Main file, imports from all other files + libs below
import time 
from requests import exceptions

from uuid import uuid1
from decimal import Decimal, getcontext
from yaspin import yaspin #send msgs to command line
from Binance import Binance

from multiprocessing.pool import ThreadPool as Pool
from functools import partial
from Database import BotDatabase

from TradeModel import TradeModel
from Strategies import *

class BotRunner:

    def __init__(self, sp, exchange, database):
        self.sp = sp
        self.exchange = exchange
        self.database = database
        self.update_balance = True
        self.ask_permission = False
        getcontext().prec = 33

    def entryOrder(self, bot_params, strategy_function, pairs, symbol_data):
        #Check pair for signals and place buy order if match is found
        sp = self.sp
        exchange = self.exchange
        database = self.database

        #get df and check for signals
        symbol = symbol_data['symbol']
        df = exchange.getSymbolKlines(symbol, bot_params['interval'])
        buy = strategy_function(df, len(df['close']) -1)

        sp.text = 'Checking for signals on: ' + symbol
        #Place buy order if there is a signal
        if buy is not False:
            i = len(df) -1
            order_id = str(uuid1())
        
            #To buy at 0.4% lower than current price
            q_qty = Decimal(bot_params['trade_allocation'])
            buy_price = exchange.roundToValidPrice(
                symbol_data = symbol_data,
                desired_price = Decimal(df['close'][i]) * Decimal(0.99))

            quantity = exchange.roundToValidQty(
                symbol_data = symbol_data,
                desired_quantity = q_qty / buy_price)

            order_params = dict(
                symbol = symbol,
                side = 'BUY',
                type = 'LIMIT',
                timeInForce = "GTC",
                price = format(buy_price, 'f'),
                quantity = format(quantity, 'f'),
                newClientOrderId = order_id)

            #Option for running bot on automatic, or having it ask user for permission to place an order
            if self.ask_permission:

                model = TradeModel(symbol, bot_params['interval'])
                model.df = df
                #Reminder buy_signals must take a list as input
                model.plot_data(buy_signals=[(df['time'][i], buy)], plot_title=symbol)   

                sp.stop()
                print(order_params)
                print('Signal found on: ' + symbol + ', place order? (y / n)?')
                permission = input()
                sp.start()
                if permission != 'y':
                    return
            
            #Buying from exchange
            order_result = self.placeOrder(order_params, bot_params['test_run'])

            if order_result is not False:
                #saving order
                self.update_balance = True
                db_order = self.orderResultToDatabase(order_result, symbol_data, bot_params, True)
                database.saveOrder(db_order)

                pairs[symbol]['is_active'] = False
                pairs[symbol]['current_order_id'] = order_id
            
                #Set pair state to inactive
                database.updatePair(
                    bot = bot_params,
                    symbol = symbol,
                    pair = pairs[symbol]
                )

    def exitOrder(self, bot_params, pairs, order:dict):
        #Check if order filled, if yes then update order in DB
        #Then place new order at target price, OCO-type if stop loss enabled

        sp = self.sp
        exchange = self.exchange

        if order['is_closed']:
            return

        symbol = order['symbol']
        exchange_order_info = exchange.getOrderInfo(symbol, order['id'])

        if not self.checkRequestValue(symbol, order['id']):
            return

        pair = pairs[symbol]

        sp.text = 'Looking for exit on: ' + symbol
        #Updating order in outdated DB
        order['status'] = exchange_order_info['status']
        order['executed_quantity'] = Decimal(exchange_order_info['executedQty'])
        if exchange_order_info['status'] == exchange.ORDER_STATUS_FILLED:
            if order['is_entry_order']:
                #Place sell order
                order_id = str(uuid1())
                price = exchange.roundToValidPrice(symbol_data = self.all_symbol_datas[symbol], desired_price=Decimal(order['take_profit_price']))
                quantity = exchange.roundToValidQty(symbol_data = self.all_symbol_datas[symbol], desired_quantity = Decimal(order['executed_quantity']))
                order_params = dict(
                    symbol = symbol,
                    side = 'SELL',
                    type = 'LIMIT',
                    timeInForce = 'GTC',
                    price = format(price, 'f'),
                    quantity = format(quantity, 'f'),
                    newClientOrderId = order_id)

                if self.ask_permission:
                    sp.stop()
                    print('Found exit on: ' + symbol)
                    print('Entry Order: ')
                    print(exchange_order_info)
                    print()
                    print("Potential Exit Order: ")
                    print(order_params)
                    print()
                    print("Place Exit Order? (y / n) ")

                    permission = input()
                    if permission != 'y':
                        return
                
                #Buying From Exchange
                order_result = self.placeOrder(order_params, bot_params['test_run'])
                if order_result is not False:
                    self.update_balance = True

                    #Save order
                    db_order = self.orderResultToDatabase(\
                        order_result, None, bot_params, False, False, order['id'])
                    database.saveOrder(db_order)

                    order['is_closed'] = True
                    order['closing_order_id'] = order_id
                    #Change status of pair to inactive
                    pair['is_active'] = False
                    pair['current_order_id'] = order_id
            else:
                self.update_balance = True
                sp.stop()
                print('Successfully exit of order on ' + symbol)
                print(order)
                print(exchange_order_info)
                sp.start()
                order['is_closed'] = True
                #order['closing_order_id'] = order['id']
                pair['is_active'] = True
                pair['current_order_id'] = None
                #pairs[symbol]['profit_loss'] = Decimal(pairs[symbol]['profit_loss']) * (Decimal(order['price]))

            pairs[symbol] = pair

            #update db
            database.updatePair(
                bot = bot_params,
                symbol = symbol,
                pair=pair
            )
        database.updateOrder(order)

    def placeOrder(self, params, test):
        ''' Create order on pair based on params. Return False if unsuccesful, otherwise
         returns order_info from exchange '''
        sp = self.sp
        exchange = self.exchange

        order_info = exchange.makeOrderFromDict(params, test=test)
        #If not able to place order, close position
        sp.stop()
        if 'code' in order_info:
            print('Error placing order!')
            print(params)
            print(order_info)
            print()
            sp.start()
            return False
        #If successful order, set pair to active
        else:
            print('Order placed successfully!')
            print(params)
            print(order_info)
            print()
            sp.start()
            return order_info
    

    def checkRequestValue(self, response, text='Error getting request from exchange.', print_response=True  ):
        #Check the return value of a request
        sp = self.sp

        if 'code' in response:
            sp.stop()
            print(text)
            if print_response:
                print(response)
                print()
            sp.start()
            return False
        else:
            return True

    
    def orderResultToDatabase(self, order_result, symbol_data, bot_params, is_entry_order=False, is_closed=False, closing_order_id=False):
        sp = self.sp
        exchange = self.exchange

        order = dict()
        if symbol_data == None:
            symbol_data = exchange.getSymbolDataOfSymbols([order_result['symbol']])
        order['id'] = order_result['clientOrderId']
        order['bot_id'] = bot_params['id']
        order['symbol'] = order_result['symbol']
        order['time'] = order_result['transactTime']
        order['price'] = order_result['price']
        order['take_profit_price'] = exchange.roundToValidPrice(
            symbol_data = symbol_data,
            desired_price = Decimal(order_result['price']) * Decimal(bot_params['profit_target']),
            round_up = True)

        order['original_quantity'] = Decimal(order_result['origQty'])
        order['executed_quantity'] = Decimal(order_result['executedQty'])
        order['status'] = order_result['status']
        order['side'] = order_result['side']
        order['is_entry_order'] = is_entry_order
        order['is_closed'] = is_closed
        order['closing_order_id'] = closing_order_id

        sp.stop()
        print('Order will be saved in DB as: ')
        print(order)
        sp.start()
        
        return order


    def createBot(self,
        name = 'Ajat_bot',
        strategy_name = 'ma_crossover',
        interval = '3m',
        trade_allocation = 0.1,
        profit_target = 1.012,
        test = False,
        symbols = []):

        sp = self.sp
        exchange = self.exchange
        database = self.database

        assert interval in exchange.KLINE_INTERVALS, interval + " is not a valid interval"
        assert trade_allocation > 0 and trade_allocation <= 1, 'Trade Allocation should be in range (0, 1)'
        assert profit_target > 0, 'Profit target must be above 0'

        symbol_datas = exchange.getSymbolDataOfSymbols(symbols)
        symbol_datas_dict = dict()
        #hold info in a dict
        for sd in symbol_datas:
            symbol_datas_dict[sd['symbol']] = sd
        
        bot_id = str(uuid1())
        bot_params = dict(
            id = bot_id,
            name = name,
            strategy_name = strategy_name,
            interval = interval,
            trade_allocation = Decimal(trade_allocation),
            profit_target = Decimal(profit_target),
            test_run = test
        )
        database.saveBot(bot_params)

        pairs = []
        for symbol_data in symbol_datas:
            pair_id = str(uuid1())
            #dict for each pair
            pair_params = dict(
                id = pair_id,
                bot_id = bot_id,
                symbol = symbol_data['symbol'],
                is_active = True,
                current_order_id = None,
                profit_loss = Decimal(1)
            )
            database.savePair(pair_params)
            pairs.append(pair_params)

        bot_params['pairs'] = pairs

        return bot_params, symbol_datas_dict

    
    def getBotFromDb(self, id):
        #Return a bot from DB based on ID
        sp = self.sp
        exchange = self.exchange
        database = self.database

        bot = database.getBot(id)
        pairs = database.getAllPairsOfBot(bot)

        symbols = []
        for pair in pairs:
            symbols.append(pair['symbol'])

        symbol_datas = exchange.getSymbolDataOfSymbols(symbols)

        symbol_datas_dict = dict()
        for sd in symbol_datas:
            symbol_datas_dict[sd['symbol']] = sd

        return bot, symbol_datas_dict


    def getAllBotsFromDb(self):
        #Return all bots in the DB, and all of their pairs

        sp = self.sp
        exchange = self.exchange
        database = self.database

        bot_sds = []
        bots = database.getAllBots()
        for bot in bots:
            pairs = database.getAllPairsOfBot(bot)

            symbols = []
            for pair in pairs:
                symbols.append(pair['symbol'])
            
            symbol_datas = exchange.getSymbolDataOfSymbols(symbols)

            symbol_datas_dict = dict()
            for sd in symbol_datas:
                symbol_datas_dict[sd['symbol']] = sd
            
            bot_sds.append((bot, symbol_datas_dict))
        
        return bot_sds


    def getBalances(self, bots):
        #Get balances of all assets in exchange
        exchange = self.exchange
        account_data = exchange.getAccountData()
        requested_times = 0

        while not self.checkRequestValue(account_data, text='\n Error getting account balance, retrying...'):
            requested_times = requested_times + 1
            time.sleep(1)
            account_data = exchange.getAccountData()

            if requested_times > 15:
                self.sp.stop()
                print("\n Cannot get balance from exchange, tried over 15 times. \n", "Stopping now. \n")
                return False, False, False

        balances_text = 'BALANCES \n'
        buy_on_bot = dict()
        quote_assets = []
        #print(type(bots))
        for bot, symbol_datas_dict in bots:
            #print(symbol_datas_dict.items(), '\n')
            for sd in symbol_datas_dict.values():
                #print(sd, '\n')
                if sd['quoteAsset'] != quote_assets:
                    quote_assets.append(sd['quoteAsset'])
            
            for bal in account_data['balances']:
                if bal['asset'] in quote_assets:
                    balances_text = balances_text + " | " + bal['asset'] + ": " + str(round(Decimal(bal['free']), 5))
                    if Decimal(bal['free']) > Decimal(bot['trade_allocation']):
                        buy_on_bot[bal['asset']] = dict(buy = True, balance = Decimal(bal['free']))
                    else:
                        buy_on_bot[bal['asset']] = dict(buy = False, balance = Decimal(bal['free']))

        return account_data, balances_text+'\n', buy_on_bot

    
    def startExecution(self, bots):
        #main execution loop:
        #Checks all pairs for symbols, places orders if they match
        #Checks all unfilled orders placed to see if they have been filed, will place subsequent order/closes

        exchange = self.exchange
        database = self.database

        if len(bots) == 0:
            self.sp.text == 'No bots available, exiting now...'
            return
        
        self.sp.text = 'Getting balances of all bots now...'
        account_data, balances_text, buy_on_bot = self.getBalances(bots)

        self.all_symbol_datas = dict()

        #Tuple pair of bot params, and all symbols traded
        for bot, sd in bots:
            pairs = database.getAllPairsOfBot(bot)
            for pair in pairs:
                self.all_symbol_datas[pair['symbol']] = sd[pair['symbol']]
        
        while True:
            with yaspin() as sp:
                self.sp = sp
                try:
                    #get all pairs
                    aps = []
                    for bot, sd in bots:
                        aps.extend(database.getAllPairsOfBot(bot))
                    all_pairs = dict()
                    for pair in aps:
                        all_pairs[pair['symbol']] = pair

                    #Only req balances if order places recently
                    if self.update_balance:
                        account_data, balances_text, buy_on_bot = self.getBalances(bot)
                        if account_data is False:
                            return
                        sp.stop()
                        print(balances_text)
                        sp.start()
                        self.update_balance = False

                    #Finding signals on bots
                    for bot, symbol_datas_dict in bots:
                        #get active pairs per bot
                        ap_symbol_datas = []
                        aps = database.getActivePairsOfBot(bot)
                        pairs = dict()
                        for pair in aps:
                            if symbol_datas_dict.get(pair['symbol'], None) == None:
                                sp.text = 'Cant find ' + pair['symbol'] + ' will look for it later.'
                            else:
                                ap_symbol_datas.append(symbol_datas_dict[pair['symbol']])
                                pairs[pair['symbol']] = pair

                        #If balance high enough, try finding more signals
                        try:
                            self.Run(bot, strategies_dict[bot['strategy_name']], pairs, ap_symbol_datas)
                        except exceptions.SSLError:
                            sp.text = 'SSL Error caught!'
                        except exceptions.ConnectionError:
                            sp.text = 'Trouble establishing connection, retrying...'
                        
                        open_orders = database.getOpenOrdersOfBot(bot)

                        #If there are open orders saved in DB, check if they have been exited
                        if len(open_orders) > 0:
                            sp.text = (str(len(open_orders)) + ' orders open on ' + bot['name'] + ', trying to close')
                            try:
                                self.Exit(bot, all_pairs, open_orders)
                            except exceptions.SSLError:
                                sp.text = 'SSL Error caught'
                            except exceptions.ConnectionError:
                                sp.text = 'Trouble connecting, retrying...'
                        else:
                            sp.text = 'No orders open on ' + bot['name']

                except KeyboardInterrupt:
                    sp.stop()
                    print('\n Exiting... \n')
                    return

    
    #Self.Run and self.Exit will be wrappers around EntryOrder and ExitOrder functions
    #Check for signals and for filled orders in parallel
    def Run(self, bot_params, strategy_function, pairs, symbol_datas):
        sp = self.sp
        exchange = self.exchange
        database = self.database

        pool = Pool(4)
        func1 = partial(self.entryOrder, bot_params, strategy_function, pairs)
        pool.map(func1, symbol_datas)
        pool.close()
        pool.join()

    def Exit(self, bot_params, pairs, orders):
        sp = self.sp
        exchange = self.exchange
        database = self.database

        pool = Pool(4)
        func1 = partial(self.ExitOrder, bot_params, pairs)
        pool.map(func1, orders)
        pool.close()
        pool.join()

    
def Main():
    sp = yaspin()
    exchange = Binance(filename='credentials.txt')
    database = BotDatabase('database.db')
    prog = BotRunner(sp, exchange, database)

    i = input('Execute or quit? (e or q) \n')
    bot_symbol_datas = []
    while i not in ['q']:
        if i == 'e':
            i = input('create a new bot? (y or n) \n')
            if i == 'y':

                symbols = ['ETHBTC', 'NEOBTC', 'EOSETH', 'BNBETH', 'BTCUSDT', \
				'ETHUSDT', 'WTCBTC', 'KNCETH', 'IOTABTC', 'LINKBTC', 'ENGBTC', \
				'DNTBTC', 'BTGBTC', 'XRPBTC', 'ENJBTC', 'BNBUSDT', 'XMRBTC', 'BATBTC', \
				'NEOUSDT', 'LTCUSDT', 'WAVESBTC', 'IOSTBTC', 'QTUMUSDT', 'XEMBTC', \
				'ADAUSDT', 'XRPUSDT', 'EOSUSDT', 'THETABTC', 'IOTAUSDT', 'XLMUSDT', \
				'ONTUSDT', 'TRXUSDT', 'ETCUSDT', 'ICXUSDT', 'VETUSDT', 'POLYBTC', \
				'LINKUSDT', 'WAVESUSDT', 'BTTUSDT', 'FETBTC', 'BATUSDT', 'XMRUSDT', \
				'IOSTUSDT', 'MATICBTC', 'ATOMUSDT', 'ALGOBTC', 'ALGOUSDT', 'DUSKBTC', \
				'TOMOBTC', 'XTZBTC', 'HBARBTC', 'HBARUSDT', 'FTTBTC', 'FTTUSDT', \
				'OGNBTC', 'OGNUSDT', 'BEARUSDT', 'ETHBULLUSDT', 'ETHBEARUSDT', \
				'WRXBTC', 'WRXUSDT', 'LTOBTC', 'EOSBEARUSDT', 'XRPBULLUSDT', \
				'XRPBEARUSDT', 'AIONUSDT', 'COTIBTC']

                bot, symbol_datas_dict = prog.createBot(
                    strategy_name='ma_crossover',
                    trade_allocation = 0.001,
                    symbols=symbols)
                bot_symbol_datas.append((bot, symbol_datas_dict))

            else:
                bot_symbol_datas = prog.getAllBotsFromDb()
            
            prog.startExecution(bot_symbol_datas)

        i = input("Execute or Quit? (e or q) ")


if __name__ == '__main__':
    Main()

                  