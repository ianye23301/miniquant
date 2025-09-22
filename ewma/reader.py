from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockSnapshotRequest
import os
from dotenv import load_dotenv

load_dotenv()

# Simple class to poll price, will probably switch to websockets soon.

class Reader:
    def __init__ (self, stockName):
        self.stock = stockName
        self.price = 0
        self.client = StockHistoricalDataClient (os.getenv("APCA-API-KEY-ID"), os.getenv("APCA-API-SECRET-KEY"))

    def poll (self):
        snapshotRequest = StockSnapshotRequest (symbol_or_symbols=[self.stock])
        return self.client.get_stock_snapshot (snapshotRequest)


def main ():
    stockName = "SPY"
    trading_client = TradingClient (os.getenv ("APCA-API-KEY-ID"), os.getenv ("APCA-API-SECRET-KEY"))
    asset = trading_client.get_asset (stockName)

    if not asset.tradable:
        print ('Stock not found')
        return

    reader = Reader (stockName)
    print (reader.poll ())


main()