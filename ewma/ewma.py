from reader import Reader
import time

import os
from dotenv import load_dotenv
from datetime import datetime

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
        self.reader = Reader(stockName)
        self.startTime = None
        self.lastProgressTime = datetime.now()
        self.position = False

    def snapshot (self):
        snapshot = self.reader.poll ()
        data = snapshot[self._stockName]['latest_quote']
        spread = data['ask_price'] - data['bid_price']
        mid = (data['ask_price'] + data['bid_price']) / 2
        timestamp = data['timestamp']
        return {'spread': spread, 'mid': mid, 'timestamp': timestamp}
    

    def enter_position(self, spread, price):
        pred = 1 * self.tau
        cost = spread / price 
        buffer = 0
        if pred > cost + buffer:
            pass
        return
    
    def exit_position(self):
        return

    def end_burst (self):
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

            cur_poll = self.snapshot ()
            mid = cur_poll['mid']
            spread = cur_poll['spread']
            
            if spread > self._maxSpread:
                self.last_mid = mid
                continue

            r_t = (mid - self.last_mid) / self.last_mid
            meaningful = abs(r_t) > self._wiggle

            if self.state == "IDLE":
                if meaningful:
                    self.dir = True if r_t > 0 else False
                    self.b = abs(r_t)
                    self.state = "BURST"
            
            else:
                if meaningful:
                    if r_t > 0 == self.dir:
                        self.b += abs(r_t)
                        self.startTime = datetime.now()
                        self.lastProgressTime = datetime.now()
                    else:
                        self.end_burst ()

                if (datetime.now() - self.lastProgressTime).total_seconds() > self._timeout:
                    self.end_burst()

            self.last_mid = mid



                







                


