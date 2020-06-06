
class Strategies:

    @staticmethod
    def maStrategy(df, i:int):
    #If price is 10% below long sma, put buy signal and return True
        
        buy_price = 0.98 * df['long_sma'][i]
        if buy_price >= df['close'][i]:
            return min(buy_price, df['high'][i])
        
        return False
    
    @staticmethod
    def bollStrategy(df, i:int):
        #if price 2% below lower bollinger, return True

        buy_price = 0.995 * df['low_boll'][i]
        if buy_price >= df['close'][i]:
            return min(buy_price, df['high'][i])
        
        return False
    