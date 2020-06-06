import pandas as pd
import requests
import json

from plotly.offline import plot
import plotly.graph_objs as pgo
from pyti.smoothed_moving_average import smoothed_moving_average as sma
from pyti.bollinger_bands import lower_bollinger_band as lbb 

from Binance import Binance

class TradeModel:

    def __init__(self, symbol, timeframe:str='4h'):
        self.symbol = symbol
        self.exchange = Binance()
        self.df = self.exchange.get_symbol_data(symbol, timeframe)
        self.last_price = self.df['close'][len(self.df['close']) -1]
        
        try:
            self.df['short_sma'] = sma(self.df['close'].tolist(), 10)
            self.df['long_sma'] = sma(self.df['close'].tolist(), 30)
            self.df['low_boll'] = lbb(self.df['close'].tolist(), 14)
        except Exception as e:
            print(' Exception when trying to computer indicators on: ' + self.symbol)
            print(e)
            return None

    #Simple candlestick chart
    def plot_data(self, buy_signals = False, sell_signals = False, plot_title:str="", indicators=[]):
        df = self.df

        #Plotting candlesticks
        candle = pgo.Candlestick(
            x=df['time'],
            open=df['open'],
            close=df['close'],
            high=df['high'],
            low=df['low'],
            name='Candlesticks')
        
        data = [candle]

        #indicators
        if indicators.__contains__('short_sma'):
            #Adding MAs
            ssma = pgo.Scatter(
                x=df['time'],
                y=df['short_sma'],
                name='Short SMA',
                line= dict(color=('rgba(102,207,255,50)')))
            data.append(ssma)

        if indicators.__contains__('long_sma'):
            lsma = pgo.Scatter(
                x=df['time'],
                y=df['long_sma'],
                name='LONG SMA',
                line= dict(color=('rgba(255,207,102,50)')))
            data.append(lsma)

        if indicators.__contains__('low_boll'):
            lowbb = pgo.Scatter(
                x=df['time'],
                y=df['low_boll'],
                name='Lower Bollinger Band',
                line= dict(color=('rgba(255,102,207,50)')))
            data.append(lowbb)

        #plots buy signals if parameter is passed
        if buy_signals:
            buys = pgo.Scatter(
                x = [i[0] for i in buy_signals],
                y = [i[1] for i in buy_signals],
                name = "BUY SIGNALS",
                mode = "markers", #for dots not line
                marker_size = 20
            )
            data.append(buys)
        
        if sell_signals:
        #Add sell signals, use 5% over buy price to start
            sells = pgo.Scatter(
                x = [i[0] for i in sell_signals],
                y = [i[1] for i in sell_signals],
                name = "SELL SIGNALS",
                mode = "markers", #for dots not line
                marker_size = 20
            )
            data.append(sells)

        #Styling, will open in an html page
        layout = pgo.Layout(title = plot_title)
        fig = pgo.Figure(data=data, layout=layout)

        plot(fig, filename='graphs/'+plot_title+'.html')
