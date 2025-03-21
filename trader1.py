import numpy as np
from datamodel import OrderDepth, TradingState, Order, Symbol
from typing import Any, List, Dict
import json

# Logger for Prosperity 3 Visualizer
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: Dict[Symbol, List[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json(["", "", conversions, "", ""]))

        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([self.truncate(self.logs, max_item_length), self.truncate(trader_data, max_item_length), conversions, "", ""]))
        self.logs = ""

    def to_json(self, value: Any) -> str:
        return json.dumps(value, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        return value[:max_length - 3] + "..." if len(value) > max_length else value

logger = Logger()


class Trader:
    def __init__(self):
        self.prices = {}  # Store historical prices per product
        self.window_size = 10  # Moving average window for mean reversion
        self.momentum_window = 5  # Lookback for momentum strategy

    def run(self, state: TradingState):
        result = {}
        trader_data = ""
        conversions = 0  # No conversion requests initially

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

            # Calculate mean price and deviation
            mean_price = np.mean(self.prices[product]) if len(self.prices[product]) >= self.window_size else mid_price
            std_dev = np.std(self.prices[product]) if len(self.prices[product]) >= self.window_size else 1

            acceptable_price = mean_price  # Dynamic acceptable price
            upper_band = mean_price + 1.5 * std_dev
            lower_band = mean_price - 1.5 * std_dev

            logger.print(f"Product: {product} | Mean: {mean_price:.2f} | Std Dev: {std_dev:.2f} | Acceptable Price: {acceptable_price:.2f}")

            # Mean Reversion Trading
            if best_ask < lower_band:
                logger.print(f"BUY {abs(order_depth.sell_orders[best_ask])} @ {best_ask}")
                orders.append(Order(product, best_ask, -order_depth.sell_orders[best_ask]))

            if best_bid > upper_band:
                logger.print(f"SELL {order_depth.buy_orders[best_bid]} @ {best_bid}")
                orders.append(Order(product, best_bid, -order_depth.buy_orders[best_bid]))

            # Momentum Trading (based on trend)
            if len(self.prices[product]) >= self.momentum_window:
                recent_trend = self.prices[product][-1] - self.prices[product][-self.momentum_window]

                if recent_trend > 0:  # Uptrend, buy
                    logger.print(f"MOMENTUM BUY {abs(order_depth.sell_orders[best_ask] // 2)} @ {best_ask}")
                    orders.append(Order(product, best_ask, -order_depth.sell_orders[best_ask] // 2))
                elif recent_trend < 0:  # Downtrend, sell
                    logger.print(f"MOMENTUM SELL {order_depth.buy_orders[best_bid] // 2} @ {best_bid}")
                    orders.append(Order(product, best_bid, -order_depth.buy_orders[best_bid] // 2))

            result[product] = orders

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
