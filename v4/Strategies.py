from Indicators import Indicators

class Strategies:

    @staticmethod
    def maStrategy(df, i:int):

        if not df.__contains__('long_sma'):
            Indicators.addIndicator(df, indicator_name='sma', col_name='long_sma', args=30)

        #If price is 4% below long sma, put buy signal and return True
        buy_price = 0.96 * df['long_sma'][i]
        if buy_price >= df['close'][i]:
            return min(buy_price, df['high'][i])
        
        return False
    
    @staticmethod
    def bollStrategy(df, i:int):
        if not df.__contains__('low_boll'):
            Indicators.addIndicator(df, indicator_name='lbb', col_name='low_boll', args=14)

        #if price 2.5% below lower bollinger, return True
        buy_price = 0.975 * df['low_boll'][i]
        if buy_price >= df['close'][i]:
            return min(buy_price, df['high'][i])
        
        return False

    @staticmethod
    def ichimokuBull(df, i:int):

        if not df.__contains__('tenkansen') or not df.__contains__('kijunsen') or not df.__contains__('senkou_a') or not df.__contains__('senkou_b'):
            Indicators.addIndicator(df, indicator_name='ichimoku', col_name=None, args=None)
    
        #Check if valid
        if i - 1 > 0 and i < len(df):
            if df['senkou_a'][i] is not None and df['senkou_b'][i] is not None:
                if df['tenkansen'][i] is not None and df['tenkansen'][i-1] is not None:
                    if (df['close'][i-1] < df['tenkansen'][i-1]) and \
                        (df['close'][i] > df['tenkansen'][i]) and \
                        (df['close'][i] > df['senkou_a'][i]) and \
                        (df['close'][i] > df['senkou_b'][i]):
                            return df['close'][i]

        return False
                      