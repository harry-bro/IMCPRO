from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import numpy as np

class Trader:
    def __init__(self):
        self.prices = {}  # Store historical prices per product
        self.window_size = 3e5  # Moving average window for mean reversion
        self.momentum_window = 1e5  # Lookback for momentum strategy

    def run(self, state: TradingState):
        result = {}
        
        for product, order_depth in state.order_depths.items():
            orders = []
            best_bid = max(order_depth.buy_orders.keys(), default=None)
            best_ask = min(order_depth.sell_orders.keys(), default=None)
            
            if best_bid is None or best_ask is None:
                continue
            
            mid_price = (best_bid + best_ask) / 2
            
            # Store price history
            if product not in self.prices:
                self.prices[product] = []
            self.prices[product].append(mid_price)
            
            # Maintain fixed window size
            if len(self.prices[product]) > self.window_size:
                self.prices[product].pop(0)
            
            # Mean Reversion Strategy
            if len(self.prices[product]) >= self.window_size:
                mean_price = np.mean(self.prices[product])
                std_dev = np.std(self.prices[product])
                
                upper_band = mean_price + 1.5 * std_dev
                lower_band = mean_price - 1.5 * std_dev

                if best_ask < lower_band:
                    # Buy signal (price too low, expecting reversion)
                    orders.append(Order(product, best_ask, -order_depth.sell_orders[best_ask]))
                
                if best_bid > upper_band:
                    # Sell signal (price too high, expecting reversion)
                    orders.append(Order(product, best_bid, -order_depth.buy_orders[best_bid]))

            # Momentum Strategy
            if len(self.prices[product]) >= self.momentum_window:
                recent_trend = self.prices[product][-1] - self.prices[product][-self.momentum_window]

                if recent_trend > 0:  # Uptrend, buy
                    orders.append(Order(product, best_ask, -order_depth.sell_orders[best_ask] // 2))
                elif recent_trend < 0:  # Downtrend, sell
                    orders.append(Order(product, best_bid, -order_depth.buy_orders[best_bid] // 2))
            result[product] = orders

        traderData = "Sample"
        conversions = 1

        return result, conversions, traderData
