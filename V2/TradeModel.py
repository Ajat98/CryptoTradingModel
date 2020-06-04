import pandas as pd
import requests
import json

from plotly.offline import plot
import plotly.graph_objs as pgo
from pyti.smoothed_moving_average import smoothed_moving_average as sma
from pyti.bollinger_bands import lower_bollinger_band as lbb 

from Binance import Binance

class TradeModel:
    def __init__(self, symbol):
        self.symbol = symbol
        self.exchange = Binance()
        self.df = self.exchange.get_symbol_data(symbol, '1h')
        self.last_price = self.df['close'][len(self.df['close']) -1]
        self.buy_signals = []

        try:
            self.df['short_sma'] = sma(self.df['close'].tolist(), 10)
            self.df['long_sma'] = sma(self.df['close'].tolist(), 30)
            self.df['low_boll'] = lbb(self.df['close'].tolist(), 14)
        except Exception as e:
            print(' Exception when trying to computer indicators on: ', self.symbol)
            print(e)
            return None

    '''
    def getData(self):
        #Creating the url
        base = 'https://api.binance.com' #base endpoint
        endpoint = '/api/v1/klines' #candlestick data
        params = '?&symbol=' + self.symbol + '&interval=1h'
        url = base + endpoint + params

        #download data
        data = requests.get(url)
        dictionary = json.loads(data.text)
        #Create df from data
        df = pd.DataFrame.from_dict(dictionary)
        df = df.drop(range(6, 12), axis=1)

        #Only the columns we want
        col_names = ['time', 'open', 'high', 'low', 'close', 'volume']
        df.columns = col_names
        
        #Convert str to floats
        for c in col_names:
            df[c] = df[c].astype(float)
        #Add moving averages
        df['short_sma'] = sma(df['close'].tolist(), 10)
        df['long_sma'] = sma(df['close'].tolist(), 30)


        #print(df)
        return df
    '''
    #Adding a simple strategy
    def strategy(self):
        df = self.df
        buy_signals = []

        #If long sma - low_price > 3% of low_price --> buy signal
        for i in range(1, len(df['close'])):
            if df['long_sma'][i] > df['low'][i] and (df['long_sma'][i] - df['low'][i]) > 0.03 * df['low'][i]:
                buy_signals.append([df['time'][i], df['low'][i]])

        self.plot_data(buy_signals=buy_signals)

    #Simple candlestick chart
    def plot_data(self, buy_signals=False):
        df = self.df

        candle = pgo.Candlestick(
            x=df['time'],
            open=df['open'],
            close=df['close'],
            high=df['high'],
            low=df['low'],
            name='Candlesticks')

        #Adding MAs
        ssma = pgo.Scatter(
            x=df['time'],
            y=df['short_sma'],
            name='Short SMA',
            line= dict(color=('rgba(102,207,255,50)')))

        lsma = pgo.Scatter(
            x=df['time'],
            y=df['long_sma'],
            name='LONG SMA',
            line= dict(color=('rgba(255,207,102,50)')))

        lowbb = pgo.Scatter(
        x=df['time'],
        y=df['low_boll'],
        name='Lower Bollinger Band',
        line= dict(color=('rgba(255,102,207,50)')))

        data = [candle, lsma, ssma, lowbb]

        #plots buy signals if parameter is passed
        if buy_signals:
            buys = pgo.Scatter(
                x = [i[0] for i in buy_signals],
                y = [i[1] for i in buy_signals],
                name = "BUY SIGNALS",
                mode = "markers" #for dots not line
            )
            

        #Add sell signals, use 5% over buy price to start
            sells = pgo.Scatter(
                x = [i[0] for i in buy_signals],
                y = [i[1]*1.05 for i in buy_signals],
                name = "SELL SIGNALS",
                mode = "markers" #for dots not line
            )

            data = [candle, lsma, ssma, buys, sells]

        #Styling, will open in an html page
        layout = pgo.Layout(title = self.symbol)
        fig = pgo.Figure(data=data, layout=layout)

        plot(fig, filename=self.symbol +'.html')

    def maStrategy(self, i:int):
        #If price is 10% below long sma, put buy signal and return True

        df = self.df
        buy_price = 0.8 * df['long_sma'][i]
        if buy_price >= df['close'][i]:
            self.buy_signals.append([df['time'][i], df['close'][i], df['close'][i] * 1.045])
            return True

        return False
    
    def bollStrategy(self, i:int):
        #if price 2% below lower bollinger, return True
        df = self.df
        buy_price = 0.98 * df['low_boll'][i]
        if buy_price >=df['close'][i]:
            self.buy_signals.append([df['time'][i], df['close'][i], df['close'][i] * 1.045])
            return True
        
        return False

def Main():
   exchange = Binance()
   symbols = exchange.get_trade_symbols()

   for symbol in symbols:
        #print(symbol)
        
        model = TradeModel(symbol)
        plot = False

        # if model.maStrategy(len(model.df['close'])-1):
        #    print('MA Strategy match on:' + symbol)
        #    plot = True
       
        if model.bollStrategy(len(model.df['close'])-1):
           print('Boll Strategy match on: ' + symbol)
           plot = True
        
        if plot:
            model.plot_data()
   

if __name__ == '__main__':
    Main()