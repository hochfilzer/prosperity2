from numpy.typing import ArrayLike
from datamodel import OrderDepth, UserId, TradingState, Order
from typing import Dict, List, Tuple
import numpy as np
import jsonpickle
import collections
from collections import defaultdict
import copy
import random
from statistics import NormalDist
from math import ceil, floor, log, sqrt
"""
The documentation/wiki can be found under this link: https://imc-prosperity.notion.site/Writing-an-Algorithm-in-Python-658e233a26e24510bfccf0b1df647858
"""

"""
This code is for experimenting in the first round. In this round we can trade
    +) AMETHYSTS, pos lim 20, apparently stable in price
    +) STARFRUIT, pos lim 20, more fluctuation
"""

"""
The idea for trading is extremely basic here: Amethysts are at a stable price at 10k. Buy anything below, sell anything above.
Through some experimentation we wrote an algorithm that helps us do this and also converge to a neutral position.
For starfruit we do the same, but instead we use as a benchmark the moving average price of the past 7 days.
This seems to work surprisingly well for historical data.
"""


class Trader:
    def run(self, state: TradingState):
        def BSM_price(spot_price, vol = 0.010119333267211992, T: float = 248):
			# Use Black Scholes to compute a "fair" option price. The option in question is a vanilla european call option.
			# Assume constant implied volatility, computed via data given by organizsers such as fair option price at a certain time
            N = NormalDist(0,1)
            K = 10_000 # Strike price for call options
            S = spot_price
            d = (log(S/K) + ((vol ** 2) / 2) * T)/(vol * sqrt(T))
            C = S * N.cdf(d) - K * N.cdf(d- vol * sqrt(T))
            return C
        def option_delta(spot_price, vol = 0.010119333267211992, T: float = 248):
			# Compute the delta of an option
            N = NormalDist(0,1)
            K = 10_000 # Strike price for call is fixed at 10k
            S = spot_price
            d = (log(S/K) + ((vol ** 2) / 2) * T)/(vol * sqrt(T))
            return N.cdf(d)

        def compute_order(state: TradingState, product: str, estimated_price: float, position_limit = 20, current_position = None) -> List[Order]:
			# Compute orders for amethysts and starfruit based on an estimated fair market price
			# The strategy for both of these was to simply market make
            open_sell_orders = state.order_depths[product].sell_orders
            open_buy_orders = state.order_depths[product].buy_orders
            if not current_position:
                current_position = int(state.position.get(product) or 0)
            orders: List[Order] = []
            estimated_price_buy, estimated_price_sell = int(round(estimated_price-0.5)), int(round(estimated_price+0.5))

            if open_sell_orders:
                best_bid, _ = list(open_sell_orders.items())[0]
            else:
                best_bid = -1e9
            if open_buy_orders:
                best_ask, _ = list(open_buy_orders.items())[0]
            else:
                best_ask = 1e9


            # First buy anything that is cheaper than estimated price
            for price, vol in open_sell_orders.items():
                if ((price < estimated_price_buy) or( (current_position < 0) and (price == estimated_price_buy))) and (current_position < position_limit):
                    order_amount = min(-vol, position_limit-current_position)
                    order_price = price
                    orders.append(Order(product, order_price, order_amount))
                    current_position += order_amount
            # Next place any other buy orders
            if current_position < position_limit:
                order_amount = position_limit-current_position
                order_price = min(estimated_price_buy-1, best_ask+1)
                orders.append(Order(product, order_price, order_amount))

            # Now we do pretty much exactly the same for sales
            # Note that we need to reload the current position because we kept track of it for buy orders earlier
            current_position = int(state.position.get(product) or 0)

            for price, vol in open_buy_orders.items():
                if ((price > estimated_price_sell) or((current_position > 0) and (price == estimated_price_sell))) and (current_position > -position_limit):
                    order_amount = max(-vol, -position_limit-current_position)
                    order_price = price
                    orders.append(Order(product, order_price, order_amount))
                    current_position += order_amount
            # Next place any other buy orders
            if current_position > -position_limit:
                order_amount = -position_limit-current_position
                order_price = max(estimated_price_sell+1, best_bid-1)
                orders.append(Order(product, order_price, order_amount))

            return orders



        def compute_order_orchid(state: TradingState, product: str) -> List[Order]:
            # This works pretty well. Idea: Extend this to add a small proportion of orders that would yield even better arb
            open_sell_orders = state.order_depths[product].sell_orders
            open_buy_orders = state.order_depths[product].buy_orders
            current_position = 0 #int(state.position.get(product) or 0)
            orders: List[Order] = []
            position_limit = 100
            south_sell = state.observations.conversionObservations[product].askPrice + state.observations.conversionObservations[product].importTariff + state.observations.conversionObservations[product].transportFees
            south_buy = state.observations.conversionObservations[product].bidPrice - state.observations.conversionObservations[product].exportTariff - state.observations.conversionObservations[product].transportFees

            certain_buy = False
            certain_sell = False

            # First buy anything that is cheaper than estimated price
            for price, vol in open_sell_orders.items():
                if (price < south_buy)  and (current_position < position_limit):
                    order_amount = min(-vol, position_limit-current_position)
                    order_price = price
                    orders.append(Order(product, order_price, order_amount))
                    current_position += order_amount
                    certain_buy = True
            # Next place any other buy orders
            if current_position < position_limit:
                order_amount = position_limit-current_position
                if certain_buy:
                    order_price = min(int(floor(south_buy)-1),list(open_sell_orders.items())[0][0] -1)
                else:
                    order_price = int(ceil(south_buy)-1)
                orders.append(Order(product, order_price, order_amount))


            # Now we do pretty much exactly the same for sales
            # Note that we need to reload the current position because we kept track of it for buy orders earlier
            current_position = 0 #int(state.position.get(product) or 0)

            for price, vol in open_buy_orders.items():
                if (price >south_sell) and (current_position > -position_limit):
                    order_amount = max(-vol, -position_limit-current_position)
                    order_price = price
                    orders.append(Order(product, order_price, order_amount))
                    current_position += order_amount
                    certain_sell = True
            # Next place any other buy orders
            if current_position > -position_limit:
                order_amount = -position_limit-current_position
                if certain_sell:
                    order_price = min(int(ceil(south_sell)+1),list(open_buy_orders.items())[0][0] +1)
                else:
                    order_price = int(floor(south_sell)+1)

                orders.append(Order(product, order_price, order_amount))


            return orders

        def compute_pair_trading_order(state: TradingState) -> Dict[str, List[Order]]:
            love_products = ["GIFT_BASKET", "STRAWBERRIES", "ROSES", "CHOCOLATE"]

            final_orders = {product: [] for product in love_products}
            pos_lim = {"GIFT_BASKET": 58, "STRAWBERRIES": 348, "ROSES": 58, "CHOCOLATE": 232}
            # Try to adjust the position limits so that we always obtain an actually balanced portfolio with the correct pairing weight
            cur_pos = {product: state.position.get(product, 0) for product in love_products}
            weights = {"ROSES": 1, "STRAWBERRIES": 6, "CHOCOLATE": 4}

            open_sell_orders = {}
            open_buy_orders = {}
            best_bid = {}
            best_ask = {}
            mid_price = {}

            for product in love_products:
                open_sell_orders = state.order_depths[product].sell_orders
                open_buy_orders = state.order_depths[product].buy_orders
                best_bid[product], _ = list(open_buy_orders.items())[0]
                best_ask[product], _ = list(open_sell_orders.items())[0]
                mid_price[product] = (best_bid[product] + best_ask[product]) / 2

            bask_diff = mid_price["GIFT_BASKET"] - mid_price["ROSES"] - 4 * mid_price["CHOCOLATE"] - 6 * mid_price["STRAWBERRIES"]  - 380
            dev = 105 #initialize threshold at which one should aggressively sell/buy
            conservative_factor = 0
            short, long = True, True
            if bask_diff > dev:
                short = True
                long = False
            elif bask_diff < -dev:
                long = True
                short = False
            else: #if the price is between long/short threshold, try to market make
                conservative_factor = 2

            if short and (bask_diff > dev/2):
                for product in ["ROSES", "CHOCOLATE", "STRAWBERRIES"]:
                    final_orders[product].append(Order(product, best_ask[product]-conservative_factor, pos_lim[product] - cur_pos[product])) #-vol * weights[product]))
                final_orders["GIFT_BASKET"].append(Order("GIFT_BASKET", best_bid["GIFT_BASKET"]-conservative_factor, -pos_lim["GIFT_BASKET"] - cur_pos["GIFT_BASKET"])) #vol))


            if long and (bask_diff < -dev/2):
                for product in ["ROSES", "CHOCOLATE", "STRAWBERRIES"]:
                    final_orders[product].append(Order(product, best_bid[product]+conservative_factor, -pos_lim[product] - cur_pos[product])) # -vol * weights[product]))
                final_orders["GIFT_BASKET"].append(Order("GIFT_BASKET", best_ask["GIFT_BASKET"]+conservative_factor, pos_lim["GIFT_BASKET"] - cur_pos["GIFT_BASKET"]))#vol))        # elif (cur_pos["GIFT_BASKET"] > 0):





            return final_orders


        def compute_option_order(state: TradingState, option_short: bool, option_long: bool) -> Tuple[Dict[str, List[Order]], bool, bool]:
            dev = 1#13.468674433832241/6.3763/2 #7.25
            coco_prods = ["COCONUT", "COCONUT_COUPON"]
            coco_orders = {prod: [] for prod in coco_prods}
            best_bid = {}
            best_ask = {}
            best_ask_vol = {}
            best_bid_vol = {}
            mid_price = {}
            for product in coco_prods:
                if list(state.order_depths[product].buy_orders.items()) and list(state.order_depths[product].sell_orders.items()):
                    open_sell_orders = state.order_depths[product].sell_orders
                    open_buy_orders = state.order_depths[product].buy_orders
                    best_bid[product], best_bid_vol[product] = list(open_buy_orders.items())[0]
                    best_ask[product], best_ask_vol[product] = list(open_sell_orders.items())[0]
                    mid_price[product] = (best_bid[product] + best_ask[product]) / 2
                    trading = True
                else:
                    trading = False
                    break
            if trading:
                cur_pos = {product: state.position.get(product, 0) for product in coco_prods}
                pos_lim = {"COCONUT": 300, "COCONUT_COUPON": 600}
                BSM_coco = BSM_price(mid_price["COCONUT"], T= 246 - state.timestamp / 1e9, vol = 0.16/sqrt(250)) # T = 1 - (state.timestamp + 3)/1e6 / 250, vol = 0.16)#

                option_diff  = 100 * (BSM_coco - mid_price["COCONUT_COUPON"])/mid_price["COCONUT_COUPON"]
                delta = option_delta(mid_price["COCONUT"], T = 246- (state.timestamp)/1e9 , vol = 0.16/sqrt(250))#T = 248 - state.timestamp / 1e7 )

                if option_diff > dev:
                    option_short = False
                    option_long = True
                elif option_diff < -dev:
                    option_short = True
                    option_long = False


                if option_long:
                    if abs(delta - 0.5) > 0.1:
                        pos_lim["COCONUT_COUPON"] = int(floor(min(600, 300/delta)))
                        pos_lim["COCONUT"] = int(floor(pos_lim["COCONUT_COUPON"] * delta))

                    if pos_lim["COCONUT_COUPON"] - cur_pos["COCONUT_COUPON"] >= 0:
                        coco_orders["COCONUT_COUPON"].append(Order("COCONUT_COUPON",best_ask["COCONUT_COUPON"], pos_lim["COCONUT_COUPON"] - cur_pos["COCONUT_COUPON"]))
                    else:
                        coco_orders["COCONUT_COUPON"].append(Order("COCONUT_COUPON",best_bid["COCONUT_COUPON"], pos_lim["COCONUT_COUPON"] - cur_pos["COCONUT_COUPON"]))


                    if -pos_lim["COCONUT"] - cur_pos["COCONUT"] <= 0:
                        coco_orders["COCONUT"].append(Order("COCONUT", best_bid["COCONUT"], -pos_lim["COCONUT"] - cur_pos["COCONUT"]))
                    else:
                        coco_orders["COCONUT"].append(Order("COCONUT", best_ask["COCONUT"] , -pos_lim["COCONUT"] - cur_pos["COCONUT"]))

                elif option_short:
                    if abs(delta - 0.5) > 0.1:
                        pos_lim["COCONUT_COUPON"] = int(floor(min(600, 300/delta)))
                        pos_lim["COCONUT"] = int(floor(pos_lim["COCONUT_COUPON"] * delta))

                    if -pos_lim["COCONUT_COUPON"] - cur_pos["COCONUT_COUPON"]<= 0:
                        coco_orders["COCONUT_COUPON"].append(Order("COCONUT_COUPON", best_bid["COCONUT_COUPON"], -pos_lim["COCONUT_COUPON"] - cur_pos["COCONUT_COUPON"]))
                    else:
                        coco_orders["COCONUT_COUPON"].append(Order("COCONUT_COUPON", best_ask["COCONUT_COUPON"], -pos_lim["COCONUT_COUPON"] - cur_pos["COCONUT_COUPON"]))


                    if pos_lim["COCONUT"] - cur_pos["COCONUT"] >= 0:
                        coco_orders["COCONUT"].append(Order("COCONUT", best_ask["COCONUT"],  pos_lim["COCONUT"] - cur_pos["COCONUT"]))
                    else:
                        coco_orders["COCONUT"].append(Order("COCONUT", best_bid["COCONUT"],  pos_lim["COCONUT"] - cur_pos["COCONUT"]))

            return coco_orders, option_short, option_long


		# Orders to be placed on exchange matching engine
        result = {}
        """
        AMETHYST ORDERS:
        """
        amethyst_estimated_price = 10_000
        amethyst_orders = compute_order(state, "AMETHYSTS", amethyst_estimated_price)
        result["AMETHYSTS"] = amethyst_orders

        # Gather cached data (historical starfruit trading price)
        if state.traderData == "":
            daily_trades: Dict[str, List[float]] = {product: [] for product in state.order_depths}
            option_short, option_long = False, False
        else:
            cache = jsonpickle.decode(state.traderData)
            daily_trades = cache[0]
            option_short: bool = cache[1]
            option_long: bool = cache[2]

        """
        STARFRUIT ORDERS:
        """
	# For starfruit orders we apply a very simple market taking/making strategey:
	# Everything that deviates strongly from a the moving average of the previous 7 timestamps was found to be a 
	# good buy/sell opportunity experimentally, which we can successfully exploit.

        product = "STARFRUIT"
        window_length = 7
        if state.order_depths[product].buy_orders and state.order_depths[product].sell_orders:
            best_ask, _ = list(state.order_depths[product].buy_orders.items())[0]
            best_bid, _ = list(state.order_depths[product].sell_orders.items())[0]
            daily_trades[product].append((best_bid + best_ask) / 2)
        else:
            daily_trades[product].append(daily_trades[product][-1])

        if len(daily_trades[product]) > window_length:
            del daily_trades[product][0]

        if state.timestamp > (window_length+1) * 100:
            mov_avg = sum(daily_trades[product][-window_length:]) / window_length # mov_avg_cache['short'][-1]


            starfruit_orders = compute_order(state, product,  mov_avg, position_limit = 20)
            print(f"Starfruit orders: {starfruit_orders}")
            result[product] = starfruit_orders

        """
        ORCHID ORDERS:
        """
        product = "ORCHIDS"

        # For orchids initially just try to use arbitrage

        orchid_orders = []
        # Convert all orchids we have since our strategy is pure arbitrage
        conversions = - state.position.get(product, 0)
        orchid_orders = compute_order_orchid(state, product)

        result[product] = orchid_orders

        """
        BASKET ORDERS:
        """


        basket_orders = compute_pair_trading_order(state)
        love_products = ["GIFT_BASKET", "STRAWBERRIES", "ROSES", "CHOCOLATE"]

        for product in love_products:
            result[product] = basket_orders[product]

        """
        COCO (OPTION) ORDERS:
        """

        coco_orders, new_short, new_long = compute_option_order(state, option_short, option_long)

        coco_products = ["COCONUT", "COCONUT_COUPON"]
        for product in coco_products:
            result[product] = coco_orders[product]


        traderData = jsonpickle.encode([daily_trades, new_short, new_long]) # pickle trading state to be loaded in next timestamp
	# Debugging statements:

        print(f"These are my orders: {result}")

        print(f"These are my positions: {state.position}")

        print(f"These are my conversions: {conversions}.")





        return result, conversions, traderData
