from reader import Reader
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass


import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class Ewma ():
    def __init__ (self, stockName, maxSpread = 0.02, wiggle = 0.0002, timeout = 5, alpha = 0.1):
        # private
        self._stockName = stockName
        self._maxSpread = maxSpread
        self._wiggle = wiggle
        self._timeout = timeout
        self._alpha = alpha

        # public
        self.state = 'IDLE'
        self.dir = None
        self.b_last = None
        self.b = 0
        self.tau = 0    
        self.last_mid = 0
        self.startTime = None
        self.lastProgressTime = datetime.now()
        self.position = False

        self.reader = Reader(stockName)
        self.tradingClient = TradingClient (os.getenv ("APCA-API-KEY-ID"), os.getenv ("APCA-API-SECRET-KEY"), paper=True)



    def snapshot (self):
        snapshot = self.reader.poll ()
        data = snapshot[self._stockName].latest_quote
        spread = data.ask_price - data.bid_price
        mid = (data.ask_price + data.bid_price) / 2
        timestamp = data.timestamp
        return {'spread': spread, 'mid': mid, 'timestamp': timestamp, 'ask': data.ask_price, 'bid': data.bid_price}
    
    def buyStock(self, mid, pred, ask, bid):

        if self.position_status ():
            print("Already bought...")
            return

        account_info = self.tradingClient.get_account()
        equity = float(account_info.equity)
        buyingPower = float(account_info.buying_power)
        equityPower = equity * 0.02 
        direction = 'BUY' if self.dir else 'SELL'
        entry_px = ask if self.dir else bid
        expected = entry_px * pred

        min_stop = max(2 * (ask - bid), 0.5 * mid * 0.0005)
        min_profit = (ask - bid) + mid*0.0003

        takeProfit = max(entry_px + min_profit, entry_px + (1 * expected)) if self.dir else min(entry_px - min_profit, entry_px - (1 * expected))
        stopLoss = min(entry_px - min_stop, entry_px - (0.5 * expected)) if self.dir else max(entry_px + min_stop, entry_px + (0.5 * expected))

        stockQty = (min(equityPower, buyingPower) * 0.995) / entry_px

        order_data = MarketOrderRequest(
            symbol=self._stockName, 
            qty=stockQty, 
            side=OrderSide[direction], 
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=takeProfit),
            stop_loss=StopLossRequest(stop_price=stopLoss)
            )
        
        market_order = self.tradingClient.submit_order(order_data)
        print(f'Buying! Market Order: {market_order}')

        return
    
    def position_status (self):
        positions = self.tradingClient.get_all_positions()
        for p in positions:
            name = p.symbol
            if name == self._stockName:
                return p
        return None

    def enter_position (self, spread, mid, ask, bid):
        pred = 1 * self.tau
        cost = (spread / mid) + 0.0001 
        buffer = 0.0003
        if pred > cost + buffer and spread < self._maxSpread:
            self.buyStock(mid, pred, ask, bid)
        return
    
    def exit_position(self):
        position = self.position_status()
        if position:
            self.tradingClient.close_position(self._stockName)
            print("Exit!")
        return

    def end_burst (self):
        print("Burst end! \n")

        self.b_last = self.b
        self.tau = self._alpha * self.b_last  + (1-self._alpha) * self.tau
        
        self.exit_position ()

        self.b = 0
        self.state = "IDLE"
        return

    def run_indefinite (self):

        # Fill data before loop
        fillData = self.snapshot ()
        self.last_mid = fillData['mid']
        
        
        while True:

            time.sleep(1)
            print("Next snapshot... \n")

            cur_poll = self.snapshot ()
            mid = cur_poll['mid']
            spread = cur_poll['spread']
            ask = cur_poll['ask']
            bid = cur_poll['bid']
            
            if spread > self._maxSpread:
                self.last_mid = mid
                continue

            r_t = (mid - self.last_mid) / self.last_mid
            meaningful = abs(r_t) > self._wiggle

            if self.state == "IDLE":
                if meaningful:
                    print("Burst start! \n")
                    self.dir = True if r_t > 0 else False
                    self.b = abs(r_t)
                    self.state = "BURST"
                    self.enter_position(spread, mid, ask, bid)
                    self.startTime = datetime.now()
                    self.lastProgressTime = datetime.now()
            
            else:
                if meaningful:
                    if (r_t > 0) == self.dir:
                        self.b += abs(r_t)
                        self.startTime = datetime.now()
                        self.lastProgressTime = datetime.now()
                    else:
                        self.end_burst ()

                if (datetime.now() - self.lastProgressTime).total_seconds() > self._timeout:
                    self.end_burst()

            self.last_mid = mid



def main ():
    stockName = "SPY"
    ewma = Ewma (stockName)
    ewma.run_indefinite ()


main()