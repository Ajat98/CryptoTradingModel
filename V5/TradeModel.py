import pandas as pd
import requests
import json

from plotly.offline import plot
import plotly.graph_objs as pgo

from Binance import Binance

class TradeModel:

    def __init__(self, symbol, timeframe:str='4h'):
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = Binance()
        self.df = self.exchange.getSymbolKlines(symbol, timeframe)
        self.last_price = self.df['close'][len(self.df['close']) -1]
        
    #For indicators, check if they are in the df to see what to plot
    #Eventually want the function to just be able to get an indicator array of inputs,
    #Plot
    def plot_data(self, buy_signals = False, sell_signals = False, plot_title:str="", 
    indicators=[
        dict(col_name='short_sma',color='indianred', name='SHORT EMA'),
        dict(col_name='50_ema', color='blue', name='50 EMA'),
        dict(col_name='200_ema', color='indianred', name='200 EMA')]):
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

        for item in indicators:
            if df.__contains__(item['col_name']):
                ssma = pgo.Scatter(
                    x=df['time'],
                    y=df[item['col_name']],
                    name=item['name'],
                    line= dict(color=(item['color'])))
                data.append(ssma)

        #indicators
        # if df.__contains__('50_ema'):
        #     #Adding MAs
        #     ssma = pgo.Scatter(
        #         x=df['time'],
        #         y=df['50_ema'],
        #         name='50 EMA',
        #         line= dict(color=('rgba(102,207,255,50)')))
        #     data.append(ssma)

        # if df.__contains__('200_ema'):
        #     #Adding MAs
        #     ssma = pgo.Scatter(
        #         x=df['time'],
        #         y=df['200_ema'],
        #         name='200 EMA',
        #         line= dict(color=('rgba(102,207,255,50)')))
        #     data.append(ssma)

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
                #x is time, y is price
                x = [i[0] for i in buy_signals],
                y = [i[1] for i in buy_signals],
                name = "Buy Signals",
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
