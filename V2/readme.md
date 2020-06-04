This version adds new class called Binance.py, will be used for making calls/requests
to Binance API (https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md)

Original model changed to use Binance.py for data instead of it's own functions. 
- Adjusted MA strategy and add BB strategy
- Implement a check if any strategies could be fulfilled and plot them if that is the case.

Goal is to make the code easier to reuse and make adding new parts/features easier.
