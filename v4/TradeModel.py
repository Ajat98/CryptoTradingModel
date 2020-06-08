import pandas as pd
import requests
import json

from plotly.offline import plot
import plotly.graph_objs as pgo

from Binance import Binance

class TradeModel:

    def __init__(self, symbol, timeframe:str='4h'):
        self.symbol = symbol
        self.exchange = Binance()
        self.df = self.exchange.get_symbol_data(symbol, timeframe)
        self.last_price = self.df['close'][len(self.df['close']) -1]
        
    #For indicators, check if they are in the df to see what to plot
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
        if df.__contains__('short_sma'):
            #Adding MAs
            ssma = pgo.Scatter(
                x=df['time'],
                y=df['short_sma'],
                name='Short SMA',
                line= dict(color=('rgba(102,207,255,50)')))
            data.append(ssma)

        if df.__contains__('long_sma'):
            lsma = pgo.Scatter(
                x=df['time'],
                y=df['long_sma'],
                name='LONG SMA',
                line= dict(color=('rgba(255,207,102,50)')))
            data.append(lsma)

        if df.__contains__('low_boll'):
            lowbb = pgo.Scatter(
                x=df['time'],
                y=df['low_boll'],
                name='Lower Bollinger Band',
                line= dict(color=('rgba(255,102,207,50)')))
            data.append(lowbb)

        #Ichimoku Cloud Indicator
        #Tekansen
        if df.__contains__('tenkansen'):
            trace = pgo.Scatter(
                x=df['time'],
                y=df['tenkansen'],
                name='Tenkansen',
                line= dict(color=('rgba(40,40,141,100)')))
            data.append(trace)
        #Kijunsen
        if df.__contains__('kijunsen'):
            trace = pgo.Scatter(
                x=df['time'],
                y=df['kijunsen'],
                name='Kijunsen',
                line= dict(color=('rgba(140,40,40,100)')))
            data.append(trace)
        #senkou A
        if df.__contains__('senkou_a'):
            trace = pgo.Scatter(
                x=df['time'],
                y=df['senkou_a'],
                name='Senkou A',
                line= dict(color=('rgba(160,240,156,100)')))
            data.append(trace)
        #Senkou B
        #Gap between senkou_a and senkou_b must be filled, usually with red or green.
        #Need to implement way to change colour of fill depending on if A or B is on top
        if df.__contains__('senkou_b'):
            trace = pgo.Scatter(
                x=df['time'],
                y=df['senkou_b'],
                name='Senkou B',
                fill = 'tonexty',
                line = dict(color=('rgba(240,160,160,50)')))
            data.append(trace)


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
        layout = pgo.Layout(
            title = plot_title,
            xaxis = {
                'title':self.symbol,
                'rangeslider': {'visible':False},
                'type' : 'date'
                },
            yaxis = {'fixedrange': False,})
            
        fig = pgo.Figure(data=data, layout=layout)
        plot(fig, filename='graphs/'+plot_title+'.html')
