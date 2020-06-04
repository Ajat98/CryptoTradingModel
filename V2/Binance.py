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
            'order': '/api/v1/order',
            'testOrder': '/api/v1/order/test',
            'allOrders': '/api/v1/allOrders',
            'klines': '/api/v1/klines',
            'exchangeInfo': '/api/v1/exchangeInfo'
        }

    #Find all current symbols tradable on binance
    def get_trade_symbols(self):
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
                all_symbols.append(pair['symbol'])
        return all_symbols

    #Pull trading data for one symbol
    def get_symbol_data(self, symbol:str, interval:str):
        params = '?&symbol=' + symbol + '&interval=' + interval
        url = self.base + self.endpoints['klines'] + params

        #download data
        data = requests.get(url)
        #print(data)
        #print(data.txt)
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

        return df


    #ORDER FUNCTION
    def makeOrder(self, symbol:str, side:str, type:str, quantity:float, price:float, test:bool=True):
        #In any pair, e.g. ETHBTC, the LHS is our base asset (ETH) which we buy, RHS is quote asset (what we sell for)
        #Quantity: how much of base asset we want, Price: How much BTC to spend on it

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

        self.signRequest(params)

        url = ''
        #Choosing between testOrder and Order endpoints
        if test:
            url = self.base + self.endpoints['testOrder']
        else:
            url = self.base + self.endpoints['order']
            
        try:
            response = requests.post(url, params=params, headers={'X-MBX-APIKEY': binance_keys['api_key']}) #Headers let this access my account
        except Exception as e:
            print('Error occured during creation of order: ', url)
            print(e)
            response = {'code': '-1', 'msg':e}
            return None

        return json.loads(response.text)

    def cancelOrder(self, symbol:str, orderId:str,):
        #Cancels an order
        params = {
            'symbol':symbol,
            'orderID':orderId,
            'recvWindow':5000,
            'timestamp': int(round(time.time()*1000))
        }
        self.signRequest(params)

        url = self.base + self.endpoints['order']
   
        try:
            response = requests.delete(url, params=params, headers={'X-MBX-APIKEY': binance_keys['api_key']}) #Headers let this access my account
        except Exception as e:
            print('Error occured during place order attempt: ', url)
            print(e)
            response = {'code': '-1', 'msg':e}
            return None

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
            response = requests.get(url, params=params, headers={'X-MBX-APIKEY': binance_keys['api_key']}) #Headers let this access my account
        except Exception as e:
            print('Error occured during get order info attempt: ', url)
            print(e)
            response = {'code': '-1', 'msg':e}
            return None

        return json.loads(response.text)

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
            response = requests.get(url, params=params, headers={'X-MBX-APIKEY': binance_keys['api_key']}) #Headers let this access my account
        except Exception as e:
            print('Error occured during attempt to get all order info on: ', url)
            print(e)
            response = {'code': '-1', 'msg':e}
            return None

        return json.loads(response.text)



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
        signature = hmac.new(binance_keys['secret_key'].encode('utf-8'), query_string.encode('utf-8'), hash.sha256)
        params['signature'] = signature.hexdigest()
