# Prosperity 2

Prosperity 2 was a trading challenge organised by IMC trading and took place in the spring of 2024.
This github repository contains the `trader.py` file that I submitted to the algorithmic part of the challenge (I will henceforth only consider the algorithmic part of the challenge).
The challenge was divided into five rounds. Each time 72 hours before a new round started we were given historical data regarding the new asset
or dynamic that would be introduced for the new round. The trading dynamic was structured as follows: At each new timestamp we had access to an
orderbook with ask and bid orders that had been unfilled from the previous round, as well as some information regarding which trades took place
during the previous timestamp. One could then place orders for the next timestamp, where in particular one could execute any trades from the open
orders before any of the bots. After this phase the remaining trades between your own trades and the bots were matched. Note: In this challenge
the trades were only ever against bots and never against other players.   

For more details regarding the trading mechanics, feel free to take a look at the offical [wiki](https://imc-prosperity.notion.site/Prosperity-2-Wiki-fe650c0292ae4cdb94714a3f5aa74c85).


My general strategy was to keep it as simple as possible since I was quite worried about overfitting on the historical data.

## Round 1
There were two tradeable products `AMETHYSTS` and `STARFRUIT`. The trading strategy for `AMETHYSTS` was essentially obvious; the price remained
more or less at a stable 10,000 seashells, and one could market make/take around that price. Trading `STARFRUIT` was similar; the price was not steady
but seemed to be moving pretty randomly but none of the moves were particularly big. I ended up just trying to  market make around the previous
price of the asset, based on some moving average computations, and fiddling around with how to optimise the orderbook. I tried all sorts of
more sophisticated variations on this approach but simply taking the moving average seemed to work most reliably for me.  This worked reasonably well
and yielded a similar PnL compared to `AMETHYSTS`.



## Round 2
This round was probably the most important round of the game. Here `ORCHIDS` were introduced. One could trade them on the main island like a regular
product but there were essentially no market making opportunities like with `STARFRUIT`. They came with a twist, though. At any given timestamp
one could trade `ORCHIDS` on the neighbouring island for a fixed price at any volume using the `conversion` method, where one needed to take
tariffs and transport costs into account. This conversion always happened at the end of a timestamp and thus it was possible to quite efficiently
arbitrage the market and make much profit. I found a good strategy but my order book logic included a rounding error, which probably prevented
me from achieving a higher Pnl (I was still satisfied with my PnL from this round).

## Round 3  
In this round four new products were introduced: `ROSES`, `CHOCOLATE`, `STRAWBERRIES` and a `GIFT_BASKET`. The `GIFT_BASKET` contains four `CHOCOLATE` bars, 
six `STRAWBERRIES` and one `ROSES`. A `GIFT_BAKET` was treated as an independent asset and could not be converted into its underlying assets (or vice versa); 
it was essentially supposed to resemble an ETF. Looking at the historical data one could determine what the premium for purchasing a gift basket was on average. 
Using this, one could try to determine whether the gift basket was relatively cheap or expensive compared to its composites, and thus make trading decisions. 
In backtests it seemed more profitable to just trade gift baskets informed by the information on the underlying, but this didn't protect against strong 
market movements. I wanted to obtain a market neutral position and thus executed a pair trading strategy. For example, if I determine that gift baskets were 
currently cheap to the price of the underlying I would purchase a gift basket and sell the corresponding amount of the composites. I found that this worked 
very well for me, and generated a good amount of PnL.  

## Round 4  
The two newly introduced assets in this round were `COCONUT` and `COCONUT_COUPON`. A `COCONUT_COUPON` functioned like a european call option on `COCONUT` with 
an expiry date of 250 trading days at a strike price of 10,000 seashells. In the video that was provided by IMC the fair option price, 250 days from expiry was 
mentioned. This enabled me to compute the implied volatility using Black Scholes. Under the (naive) assumption that the implied volatility would remain constant 
for the remainder of the trading period one could compute the fair price of `COCONUT_COUPON`. Based on this I either bought or sold `COCONUT_COUPON`, and to 
remain in a market neutral position I delta hedged using `COCONUT`. I should also note here that it was not possible to exercise the coupons at any point 
and should really be considered as an independent asset.   

## Round 5  
Here the organizers did not introduce any new assets or trading mechanics but instead released historical data regarding which bots made which trades. We could 
also access this data during the trading simulation. I am sure there were patterns here but to be honest I could not find anything too convincing and so I did 
not change my trading logic at all from the previous round. I still improved my placement and achieved very decent PnL.  

## Results  
I ended up on rank 42 out of over 9,000 participating teams.

## Backtester  
I would like to thank Jasper Merle for an extremely useful [backtester](https://github.com/jmerle/imc-prosperity-2-backtester) which I extensively used.
  


