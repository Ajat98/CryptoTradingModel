#Will be used to calculate indicators from a df

from pyti.smoothed_moving_average import smoothed_moving_average as sma
from pyti.exponential_moving_average import exponential_moving_average as ema
from pyti.bollinger_bands import lower_bollinger_band as lbb
from pyti.bollinger_bands import upper_bollinger_band as ubb
#Will add more as needed
#RSI, MACD, VWAP

'''
#Computing ichimoku cloud
For buy signals:
If price about lowest line of cloud --> bullish bias
If price moves below base line --> pullback
if price moves above conversion line --> upturn
'''
def getIchimokuCloud(df):
    
    '''Components (from python for finance blog)
    https://www.pythonforfinance.net/2019/06/26/ichimoku-trading-strategy-with-python/
    '''

    #Tenkan-sen (conversion line): (9 period high + 9 period low) / 2
    nine_period_high = df['high'].rolling(window=9).max()
    nine_period_low = df['low'].rolling(window=9).min()
    df['tenkansen'] = (nine_period_high + nine_period_low) / 2

    #Kijun-sen (Base Line): (26 p high + 26 p low) / 2
    period26_high = df['high'].rolling(window=26).max()
    period26_low = df['low'].rolling(window=26).min()
    df['kijunsen'] = (period26_high + period26_low) / 2

    #Senkou Span A (leading span A): (Conversion line + base line) / 2
    df['senkou_a'] = ((df['tenkansen'] + df['kijunsen']) / 2).shift(26)

    #Senkou Span B
    period52_high = df['high'].rolling(window=52).max()
    period52_low = df['low'].rolling(window=52).min()
    df['senkou_b'] = ((period52_high + period52_low) / 2).shift(52)

    # The most current closing price plotted 26 time periods behind (optional)
    df['chikou_span'] = df['close'].shift(-26)

    return df


#Func to compute any indicator and add to the df, called from outside class when TradeModel.py calls for an indicator for a strategy

class Indicators:

    #All indicators that have been created
    indicators_dict = {
        'sma': sma,
        'ema': ema,
        'lbb': lbb,
        'ubb': ubb,
        'ichimoku': getIchimokuCloud
    }

    @staticmethod
    def addIndicator(df, indicator_name, col_name, args):
        #Df is df to add indicator to,
        #indicator name comes from abvoe dict
        #col_name is name of new col to be added to the df
        #args for potential other arguments during function call

        try:
            #special case, where more columns created in df
            if indicator_name == 'ichimoku':
                df = getIchimokuCloud(df)
            else:
                df[col_name] = Indicators.indicators_dict[indicator_name](df['close'].tolist(), args)
        except Exception as e:
            print('Error raised when trying to compute: '+ indicator_name)
            print(e)


