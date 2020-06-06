import json
import requests
import pandas as pd
import decimal
import hmac
import time

#Binance Keys
binance_keys = {
    'api_key':'',
    'api_secret': ''
}
 

class Binance:
    def __init__(self):
        self.base = 'https://api.binance.com'

        #Every endpoint of the API that will be used
        self.endpoints = {
            'order': '/api/v3/order',
            'testOrder': '/api/v3/order/test',
            'allOrders': '/api/v3/allOrders',
            'klines': '/api/v3/klines',
            'exchangeInfo': '/api/v3/exchangeInfo'
        }

        self.headers = {'X-MBX-APIKEY': binance_keys['api_key']}

    #Find all current symbols tradable on binance
    def get_trade_symbols(self, quoteAssets: list=None):
        url = self.base + self.endpoints['exchangeInfo']

        try:
            response = requests.get(url)
            data = json.loads(response.text)
        except Exception as e:
            print('Error occured during access of symbol info at: ', url)
            print(e)
            return []

        all_symbols = []

        for pair in data['symbols']:
            if pair['status'] == 'TRADING':
                if quoteAssets != None and pair['quoteAsset'] in quoteAssets:
                    all_symbols.append(pair['symbol'])
        return all_symbols

    #Pull trading data for one symbol
    '''
    #Symbol: str of symbol to get trading data for
    #Params: 
        mins: '1m', '3m', '5m', '15m', '30m'
        hours: '1h', '2h', '4h', '6h', '8h', '12h'
        days: '1d', '3d'
        weeks: '1w'
        months: '1M'
    '''
    def get_symbol_data(self, symbol:str, interval:str):
        params = '?&symbol=' + symbol + '&interval=' + interval
        url = self.base + self.endpoints['klines'] + params

        #download data
        data = requests.get(url)
        dictionary = json.loads(data.text)

        #Create df from data
        df = pd.DataFrame.from_dict(dictionary)
        df = df.drop(range(6, 12), axis=1)

        #Only the columns we want
        col_names = ['time', 'open', 'high', 'low', 'close', 'volume']
        df.columns = col_names

        #Convert str vals to float
        for c in col_names:
            df[c] = df[c].astype(float)

        #Add a date colmn
        df['date'] = pd.to_datetime(df['time']*1000000, infer_datetime_format=True)

        return df


    #Places an Order
    def makeOrder(self, symbol:str, side:str, type:str, quantity:float, price:float, test:bool=True):
        '''
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
            'timeInForce:': 'GTC',
            'quantity':quantity,
            'price': self.floatToString(price),
            'recvWindow':5000,
            'timestamp': int(round(time.time()*1000))
        }

        #Checking for type of order
        if type != 'MARKET':
            params['timeInForce'] = 'GTC' 
            params['price'] = self.floatToString(price)

        self.signRequest(params)

        url = ''
        #Choosing between testOrder and Order endpoints
        if test:
            url = self.base + self.endpoints['testOrder']
        else:
            url = self.base + self.endpoints['order']
            
        try:
            response = requests.post(url, params=params, headers={self.headers}) #Headers let this access my account
            data = response.txt
        except Exception as e:
            print('Error occured during creation of order: ', url)
            print(e)
            data = {'code': '-1', 'msg':e}

        return json.loads(data)

    def cancelOrder(self, symbol:str, orderId:str,):
        #Cancels an order on a symbol using orderId

        params = {
            'symbol':symbol,
            'orderID':orderId,
            'recvWindow':5000,
            'timestamp': int(round(time.time()*1000))
        }
        self.signRequest(params)

        url = self.base + self.endpoints['order']
   
        try:
            response = requests.delete(url, params=params, headers=self.headers) 
            data = response.text
        except Exception as e:
            print('Error occured during place order attempt: ', url)
            print(e)
            data = {'code': '-1', 'msg':e}
            
        return json.loads(data)

    #Info about a particular order
    def getOrderInfo(self, symbol:str, orderId:str,):
        #Info about an order based on the orderId
        params = {
            'symbol':symbol,
            'orderID':orderId,
            'recvWindow':5000,
            'timestamp': int(round(time.time()*1000))
        }
        self.signRequest(params)

        url = self.base + self.endpoints['order']

        try:
            response = requests.get(url, params=params, headers=self.headers) #Headers let this access my account
            data = response.text
        except Exception as e:
            print('Error occured during get order info attempt: ', url)
            print(e)
            data = {'code': '-1', 'msg':e}

        return json.loads(data)

    #Get ALL order info
    def getAllOrderInfo(self, symbol:str):
        #Gets all orders on account for a symbol
        params = {
            'symbol':symbol,
            'timestamp': int(round(time.time()*1000))
        }
        self.signRequest(params)

        url = self.base + self.endpoints['allOrders']
        
        try:
            response = requests.get(url, params=params, headers=self.headers) #Headers let this access my account
            data = response.text
        except Exception as e:
            print('Error occured during attempt to get all order info on: ', url)
            print(e)
            data = {'code': '-1', 'msg':e}
            
        return json.loads(data)


    #Helper funcs
    #Convert float to a string, avoids scientific notation
    def floatToString(self, f:float):
        ctx = decimal.Context()
        ctx.prec = 12
        d1 = ctx.create_decimal(repr(f))
        return format(d1, 'f')

    #Signs place and cancel orders sent to binance
    def signRequest(self, params:dict):
        query_string = '&'.join(["{}={}".format(d, params[d]) for d in params])
        #Research dis line
        signature = hmac.new(binance_keys['secret_key'].encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        params['signature'] = signature.hexdigest()
