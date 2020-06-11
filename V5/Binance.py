import json
import requests
import pandas as pd
import decimal
import hmac
import time
import hashlib
from decimal import Decimal

#Start at 0, increment by 2000 if getting errors
#Tells binance that request was sent later than actually was
request_delay = 1000

class Binance:
    #Constants
    ORDER_STATUS_NEW = 'NEW'
    ORDER_STATUS_PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    ORDER_STATUS_FILLED = 'FILLED'
    ORDER_STATUS_CANCELLED = 'CANCELLED'
    ORDER_STATUS_PENDING_CANCEL = 'PENDING_CANCEL'
    ORDER_STATUS_REJECTED = 'REJECTED'
    ORDER_STATUS_EXPIRED = 'EXPIRED'

    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'

    ORDER_TYPE_LIMIT = 'LIMIT'
    ORDER_TYPE_MARKET = 'MARKET'
    ORDER_TYPE_STOP_LOSS = 'STOP_LOSS'
    ORDER_TYPE_STOP_LOSS_LIMIT = 'STOP_LOSS_LIMIT'
    ORDER_TYPE_TAKE_PROFIT = 'TAKE_PROFIT'
    ORDER_TYPE_TAKE_PROFIT_LIMIT = 'TAKE_PROFIT_LIMIT'
    ORDER_TYPE_LIMIT_MAKER = 'LIMIT_MAKER'

    KLINE_INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

    def __init__(self, filename=None):
        self.base = 'https://api.binance.com'

        #Every endpoint of the API that will be used
        self.endpoints = {
            'order': '/api/v3/order',
            'testOrder' : '/api/v3/order/test',
            'allOrders' : '/api/v3/allOrders',
            'klines' : '/api/v3/klines',
            'exchangeInfo': '/api/v3/exchangeInfo',
            '24hrTicker' : '/api/v3/ticker/24hr',
            'averagePrice': '/api/v3/avgPrice',
            'orderBook' : '/api/v3/depth',
            'account' : '/api/v3/account'
        }
        self.account_access = False

        #Read in credentials from txt file
        if filename == None:
            return

        f = open(filename, 'r')
        contents = []
        if f.mode == 'r':
            contents = f.read().split('\n')

        self.binance_keys = dict(api_key = contents[0], api_secret = contents[1])
        self.headers = {'X-MBX-APIKEY': self.binance_keys['api_key']}
        self.account_access = True

    def _get(self, url, params=None, headers=None) -> dict:
        #Will make a get request
        try:
            response = requests.get(url, params=params, headers=headers)
            data = json.loads(response.text)
            data['url'] = url
        except Exception as e:
            print('Error occured during access to: ' +url)
            print(e)
            data = {'code' : '-1', 'url' : url, 'msg':e}
        return data
        
    def _post(self, url, params=None, headers=None) -> dict:
        #Function to make a post request
        try:
            response = requests.post(url, params=params, headers=headers)
            data = json.loads(response.text)
            data['url'] = url
        except Exception as e:
            print('Error occured during access to: ' +url)
            print(e)
            data = {'code' : '-1', 'url' : url, 'msg':e}
        return data


    #Find all current symbols tradable on binance
    def getTradeSymbols(self, quoteAssets:list=None):
        url = self.base + self.endpoints['exchangeInfo']
        data = self._get(url)
        if data.__contains__('code'):
            return []

        symbols_list = []
        for pair in data['symbols']:
            if pair['status'] == 'TRADING':
                if quoteAssets != None and pair['quoteAsset'] in quoteAssets:
                    symbols_list.append(pair['symbol'])

        return symbols_list

    def getSymbolDataOfSymbols(self, symbols:list=None):
        #Get all tradeable symbols at the time of function call

        url = self.base + self.endpoints['exchangeInfo']
        data = self._get(url)
        if data.__contains__('code'):
            return []

        symbols_list = []
        for pair in data['symbols']:
            if pair['status'] == 'TRADING':
                if symbols != None and pair['symbol'] in symbols:
                    symbols_list.append(pair)
        
        return symbols_list

    def getSymbolKlinesExtra(self, symbol:str, interval:str, limit:int=1000, end_time=False):
        #Will call getSymbolData as many times as needed
        #To get historical data based on limit parameter
        #Merge results into one df

        repeat_rounds = 0
        if limit > 1000:
            repeat_rounds = int(limit/1000)

        initial_limit = limit % 1000
        if initial_limit == 0:
            initial_limit = 1000

        #get last initial_limit candles first, start and end_time
        #and go backwards, if end_time False then start at present time
        df = self.getSymbolKlines(symbol, interval, limit=initial_limit, end_time = end_time)
        while repeat_rounds > 0:
            #For every 1000 candles, grab them but starting from beginning of previous candle data
            df2 = self.getSymbolKlines(symbol, interval, limit=1000, end_time = df['time'][0])
            df = df2.append(df, ignore_index = True)
            repeat_rounds = repeat_rounds -1

        return df

    def getAccountData(self) -> dict:
        #get balances/account data
        url = self.base + self.endpoints['account']

        params = {
            'recvWindow' : 6000,
            'timestamp' : int(round(time.time()*1000)) + request_delay 
        }
        self.signRequest(params)

        return self._get(url, params, self.headers)

    def get24hrTicker(self, symbol:str):
        url = self.base + self.endpoints['24hrTicker'] + "?symbol=" + symbol
        return self._get(url)

    def getSymbolKlines(self, symbol:str, interval:str, limit:int=1000, end_time=False):
        ''' Pull trading data for only 1 symbol
        Parameters:
            symbol str:     symbol to get trading data on
            interval str:   interval to get trading data on
                minutes -   '1m', '3m', '5m', '15m', '30m'
                hours -     '1h', '2h', '4h', '6h', '8h', '12h'
                days -      '1d', '3d'
                weeks -     '1w'
                months -    '1M'
        '''

        if limit > 1000:
            return self.getSymbolKlinesExtra(symbol, interval, limit, end_time)
        
        params = '?&symbol=' + symbol + '&interval=' + interval + '&limit=' + str(limit)
        if end_time:
            params = params + '&endTime=' + str(int(end_time))

        url = self.base + self.endpoints['klines'] + params

        #Downloading data
        data = requests.get(url)
        dictionary = json.loads(data.text)
        #clean up and put in df
        df = pd.DataFrame.from_dict(dictionary)
        df = df.drop(range(6, 12), axis = 1)
        #Rename cols
        col_names = ['time', 'open', 'high', 'low', 'close', 'volume']
        df.columns = col_names
        #Convert col vals from str to float
        for c in col_names:
            df[c] = df[c].astype(float)
        
        df['date'] = pd.to_datetime(df['time'] * 1000000, infer_datetime_format = True)
        return df

    def makeOrderFromDict(self, params, test:bool=False):
        #creates order from params dict

        params['recvWindow'] = 5000
        params['timestamp'] = int(round(time.time()*1000)) + request_delay

        self.signRequest(params)
        url = ''
        if test:
            url = self.base + self.endpoints['testOrder']
        else:
            url = self.base + self.endpoints['order']

        return self._post(url, params, self.headers)

    #Places an Order
    def makeOrder(self, symbol:str, side:str, type:str, quantity:float=0, price:float=0, test:bool=True):
        '''
        Places order on Binance
        In any pair, e.g. ETHBTC, the LHS is our base asset (ETH) which we buy, RHS is quote asset (what we sell for)
        Params:
            strs:
                symbol: symbol to get trading data for
                side: side of order, e.g. BUY or SELL
                type: type of order, LIMIT, MARKET, or STOP_LOSS
            floats:
                quantity
        '''

        params = {
            'symbol':symbol,
            'side': side, #this means buy or sell
            'type': type, #Market, Limit, Stop Loss, Margin etc.ArithmeticError
            'quoteOrderQty':quantity,
            'recvWindow':5000,
            'timestamp': int(round(time.time()*1000)) + request_delay
        }

        #Checking for type of order
        if type != 'MARKET':
            params['timeInForce'] = 'GTC' 
            params['price'] = Binance.floatToString(price)

        self.signRequest(params)

        url = ''
        #Choosing between testOrder and Order endpoints
        if test:
            url = self.base + self.endpoints['testOrder']
        else:
            url = self.base + self.endpoints['order']
        
        return self._post(url, params=params, headers=self.headers)

    def cancelOrder(self, symbol:str, orderId:str):
        #Cancels an order on a symbol using orderId

        params = {
            'symbol':symbol,
            'orderID':orderId,
            'recvWindow':5000,
            'timestamp': int(round(time.time()*1000)) + request_delay
        }
        self.signRequest(params)

        url = self.base + self.endpoints['order']
   
        try:
            response = requests.delete(url, params=params, headers=self.headers) 
            data = response.text
        except Exception as e:
            print('Error occured during cancellation of order on: ', url)
            print(e)
            data = {'code': '-1', 'msg':e}
            
        return json.loads(data)

    #Info about a particular order
    def getOrderInfo(self, symbol:str, orderId:str,):
        #Info about an order based on the orderId
        params = {
            'symbol':symbol,
            'origClientOrderId': orderId,
            'recvWindow': 5000,
            'timestamp': int(round(time.time()*1000)) + request_delay 
        }
        self.signRequest(params)

        url = self.base + self.endpoints['order']

        return self._get(url, params=params, headers=self.headers)


    def getAllOrderInfo(self, symbol:str):
        #Gets all orders on account for a symbol
        params = {
            'symbol':symbol,
            'timestamp': int(round(time.time()*1000)) + request_delay
        }
        self.signRequest(params)

        url = self.base + self.endpoints['allOrders']
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            data=response.text
        except Exception as e:
            print('Error occured during get info on all orders on: ' + url)
            print(e)
            data = {'code': '-1', 'msg': e}

        return json.loads(data)


    
    def signRequest(self, params:dict):
        #Signs any request to Binance API
        query_string = '&'.join(["{}={}".format(d, params[d]) for d in params])
        #Research dis line
        signature = hmac.new(self.binance_keys['api_secret'].encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        params['signature'] = signature.hexdigest()

    #Convert float to a string, avoids scientific notation
    @classmethod
    def floatToString(cls, f:float):
        ctx = decimal.Context()
        ctx.prec = 12
        d1 = ctx.create_decimal(repr(f))
        return format(d1, 'f')
    

    #Functions for rounding prices/quantities to send to exchange, fit requirements of pair being traded
    @classmethod
    def get10Factor(cls, num):
        #Return num of 0s before first non-0 digit of a num
        #if abs(num) is less than 1 or negative num of digits between first int digit and last
        #integer digit if abs(num) >= 1
        #e.g. get10factor(0.00000164763) = 6
        #e.g. get10factor(1600623.3) = -6

        p = 0
        for i in range(-20, 20):
            if num == num % 10**i:
                p = -(i - 1)
                break
        return p
    
    @classmethod
    def roundToValidPrice(cls, symbol_data, desired_price, round_up:bool=False) -> Decimal:
        #Returns min qty of symbol we can buy, closed to desired_price

        pr_filter = {}
        for fil in symbol_data['filters']:
            if fil['filterType'] == 'PRICE_FILTER':
                pr_filter = fil
                break
        
        if not pr_filter.keys().__contains__('tickSize'):
            raise Exception('Cant find tickSize or PRICE_FILTER in symbol_data.')
            return
        
        round_off_num = int(cls.get10Factor((float(pr_filter['tickSize']))))

        num = round(Decimal(desired_price), round_off_num)
        if round_up:
            num = num + Decimal(pr_filter['tickSize'])
        
        return num

    @classmethod
    def roundToValidQty(cls, symbol_data, desired_quantity, round_up:bool=False):
        #Returns min qty of a symbol we can buy, closest to desired price
        lot_filter = {}

        for fil in symbol_data['filters']:
            if fil['filterType'] == 'LOT_SIZE':
                lot_filter = fil
                break
        
        if not lot_filter.keys.__contains__('stepSize'):
            raise Exception('Cant find stepSize or PRICE_FILTER in symbol_data.')
            return
        
        round_off_num = int(cls.get10Factor((float(lot_filter['stepSize']))))

        num = round(Decimal(desired_quantity), round_off_num)
        if round_up:
            num = num + Decimal(lot_filter['stepSize'])
        
        return num


def Main():
    symbol = 'NEOBTC'
    client_id = '73a40bae-61c7-11ea-8e67-f40f241d61b4'
    exchange = Binance('credentials.txt')
    
    d = exchange.getOrderInfo(symbol, client_id)
    print(d)

if __name__ == '__main__':
    Main()


