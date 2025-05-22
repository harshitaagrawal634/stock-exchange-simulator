import random
import heapq
import time

class Order:
    """Represents a Buy/Sell Order"""
    def __init__(self,trader_id, security, price, quantity, order_type, timestamp, oms):
        self.trader_id = trader_id
        self.security = security
        self.price = price
        self.quantity = quantity
        self.order_type = order_type  # "BUY" or "SELL"
        self.timestamp = timestamp # Orders follow price-time priority
        self.oms=oms

    def __lt__(self, other):
        """Sorting orders for price-time priority in heaps."""
        if self.price == other.price:
            return self.timestamp < other.timestamp  # Earlier orders get priority
        return self.price > other.price if self.order_type == "BUY" else self.price < other.price

class StockExchange:
    """Simulates a Stock Exchange with Order Matching Engine"""
    def __init__(self):
        self.order_books = {}  # Dictionary to store order books for each stock
        self.current_prices = {
            "AAPL": 1, "TSLA": 2, "MSFT": 3, "GOOG": 4, "AMZN": 5
        }  # Initial prices for each stock

        for security in self.current_prices:
            self.order_books[security] = {"bids": [], "asks": []}  # Separate book per stock
    def place_order(self, order):
        """Places an order into the correct security's order book and attempts to match."""
        security = order.security
        order_book = self.order_books[security]

        if order.order_type == "BUY":
            heapq.heappush(order_book["bids"], (-order.price, order))  # Max heap for bids
        else:
            heapq.heappush(order_book["asks"], (order.price, order))  # Min heap for asks

        self.match_orders(security)

    def match_orders(self, security):
        order_book = self.order_books[security]
        fixed_quantity = 1000 
        while order_book["bids"] and order_book["asks"]:
            best_bid = heapq.heappop(order_book["bids"])[1]  # Get highest bid
            best_ask = heapq.heappop(order_book["asks"])[1]  # Get lowest ask
            if best_bid.trader_id==best_ask.trader_id: # to make sure that same trader does not buy and sell the same security
                break
            else:
                if best_bid.price >= best_ask.price:  
                    buyer_pays = best_bid.price
                    seller_receives = best_ask.price
                    
                    self.current_prices[security] = best_bid.price  

                    buyer_oms = best_bid.oms  # Get buyer's OMS
                    seller_oms = best_ask.oms  # Get seller's OMS

                    buyer_oms.edit_account(security, buyer_pays, fixed_quantity, "BUY",best_bid.trader_id)  # Deduct cash, add stocks
                    seller_oms.edit_account(security, seller_receives, fixed_quantity, "SELL", best_ask.trader_id)  # Add cash, remove stocks

                else:
                    
                    heapq.heappush(order_book["bids"], (-best_bid.price, best_bid))
                    heapq.heappush(order_book["asks"], (best_ask.price, best_ask))
                    break  # Stop matching if no more trades are possible


    def get_best_bid_ask(self, security):
        """Returns the best bid and ask for a given security."""
        order_book = self.order_books[security]
        best_bid = -order_book["bids"][0][0] if order_book["bids"] else None
        best_ask = order_book["asks"][0][0] if order_book["asks"] else None
        return best_bid, best_ask

class OrderManagementSystem:
    """Manages trader's cash & portfolio"""
    def __init__(self,bank_balance, initial_cash_trading, portfolio, exchange):
        self.bank_balance=bank_balance
        self.cash = initial_cash_trading
        self.portfolio = portfolio
        self.exchange=exchange

    def portfolio_value_current(self, security, quantity):
        """Updates the trader's portfolio after a trade."""
        self.portfolio[security] = self.portfolio.get(security, 0) + quantity

    def can_place_order(self, price, quantity, order_type, security): 
        """Checks if the trader can afford the trade."""
        if order_type == "BUY":
            return self.cash >= price * quantity
        elif order_type == "SELL":
            return self.portfolio.get(security, 0) >= quantity
        return False

    def edit_account(self, security, price, quantity, order_type, trader_idd):
        # called by SE to update the trader of the order executed
        if order_type == "BUY":
            if self.cash < price*quantity:  
                print(f" Trade Rejected for: {security} as {trader_idd} does not have enough cash!\n")
                return
            self.cash -= price * quantity
            self.portfolio_value_current(security, quantity)
            print(f"{trader_idd} pays: ${price} per share for {security}")
            
        else:
            if self.portfolio.get(security, 0) < quantity:  # Prevents negative stocks
                print(f"Trade Rejected for: {security} as {trader_idd} does not have enough stocks!\n")
                return 
            self.cash += price * quantity
            self.portfolio_value_current(security, -quantity)
            print(f"{trader_idd} receives: ${price} per share for {security}")

    def add_cash(self,quantity, price_choice):
        print(f"amount needed {quantity*price_choice}\n")
        amt=int(input(f"Current bank_balance: {self.bank_balance}, current trading_balance={self.cash}, how much do you want to transfer?\n"))
        if self.bank_balance >= amt:
                self.cash += amt
                self.bank_balance-=amt
                print(f"Transferred {amt} from bank to trading account. Bank Balance: {self.bank_balance}, Trading Cash: {self.cash}\n")
        else:
            print(f"Insufficient funds in bank. Available: {self.bank_balance}\n")
            return 0
        
    def place_buy(self,trader_id,security, quantity, price_choice, t):
        if(self.can_place_order(price_choice,quantity,"BUY",security)):
            order=Order(trader_id, security, price_choice, quantity, "BUY",t,self)
            self.exchange.place_order(order)
        else:
            print(f"Insufficient funds for transaction of security {security} for {trader_id}. Available: {self.cash}")
            ch=input("Do you wan to transfer cash? y/n\n")
            if(ch=='y'):
                self.add_cash(quantity, price_choice)

    def place_sell(self,trader_id,security, quantity, price_choice, t):
        if(self.can_place_order(price_choice,quantity,"SELL",security)):
            order=Order(trader_id, security, price_choice, quantity, "SELL",t,self)
            self.exchange.place_order(order)
        else:
            print("{trader_id} does not have enough securities {security} to sell\n")


class Trader:
    """Simulates a Trader who places orders randomly"""
    def __init__(self, trader_id, oms, exchange, active):
        self.trader_id = trader_id
        self.oms = oms
        self.exchange = exchange
        self.active=active

    def action(self, security,t):
        """Trader randomly decides to buy/sell at best bid, best ask, or mid price"""
        best_bid, best_ask = self.exchange.get_best_bid_ask(security)
        last_price = self.exchange.current_prices[security]

        if best_bid and best_ask:
            price_choice = random.choice([best_bid, best_ask, (best_bid + best_ask) / 2])
        else:
            price_choice = last_price * random.uniform(0.95, 1.05)  # Randomly adjust price if no order book exists

        order_type = random.choice(["BUY", "SELL"])
        quantity = 1000  # Fixed order size

        if(order_type=="BUY"):
        
            self.oms.place_buy(self.trader_id,security, quantity, price_choice, t)
        else:
            self.oms.place_sell(self.trader_id,security, quantity, price_choice, t)
    def activeness(self):
        if(self.oms.bank_balance<1000):
            self.active=False
        return self.active

        
class Simulation:
    """Runs the trading simulation with 5 traders and 5 securities."""
    def __init__(self, num_traders, trading_hours):
        self.exchange = StockExchange()
        self.traders = []
        self.sec = ["AAPL", "TSLA", "MSFT", "GOOG", "AMZN"]  # 5 securities
        self.num_traders=num_traders
        self.trading_seconds = int(trading_hours * 3600)

        for i in range(num_traders):
            
            portfolio= {"AAPL":random.randint(1000,10000), "TSLA":random.randint(1000,10000), "MSFT": random.randint(1000,10000), "GOOG": random.randint(1000,10000), "AMZN" : random.randint(1000,10000)}
            oms = OrderManagementSystem(bank_balance= random.randint(50000, 100000),initial_cash_trading=random.randint(5000, 20000), portfolio= portfolio, exchange=self.exchange)
            trader = Trader(f"Trader_{i+1}", oms, exchange=self.exchange, active=True)
            self.traders.append(trader)

    def run(self):
        """Simulates trading day with multiple securities"""
        
        for second in range(self.trading_seconds):
            list_active_traders=[trader for trader in self.traders if trader.activeness()]
            if(len(list_active_traders)==1):
                break
            else:
                for trader in (list_active_traders):
                    val=random.random()
                    if(val>=0.5):
                        security = random.choice(self.sec)  # Random stock
                        trader.action(security, second)

        # End-of-day results
        print("\nFinal Prices:")
        for s in self.sec:
            best_bid, best_ask = self.exchange.get_best_bid_ask(s)
            print(f"{s}: Best Bid = {best_bid}, Best Ask = {best_ask}")

        for trader in self.traders:
            print(f"{trader.trader_id} Final Total Cash Left: {trader.oms.cash+trader.oms.bank_balance}, Portfolio: {trader.oms.portfolio}")

# Run the Simulation
simulation = Simulation(num_traders=5, trading_hours=6.5)
simulation.run()
