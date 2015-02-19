#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.transaction import *
from exchanges.order import *
from utilz.log import *
from utilz.object import *

class ExchangePair(object):
	"""
	This is a generic class to handle a pair in a bitcoin stock exchanges

	Such pair is defined as follow:
	CONVENTION: baseCurrency / quoteCurrency Bid / Ask
	BUY (= buy base currency)	- ask * quoteCurrency => baseCurrency
	SELL (= sell base currency)	- baseCurrency => bid * quoteCurrency
	SPREAD - ask - bid (ask >= bid)

	Example:
		EUR/USD 1.4745/1.4746
		BUY: 1.4746 USD => 1 EUR
		SELL: 1 EUR => 1.4745 USD
		SPREAD = 1.4746 - 1.4745 = 0.0001
	"""
	DEFAULT_CONFIG = {
		# Initial Currency
		'baseCurrency': None,
		# Currecny to trade into
		'quoteCurrency': None,
		# Selling
		'sell': None,
		# Buying
		'buy': None,
		# Transfer to another exchange
		'transfer': None,
		# Money withdraw
		'withdraw': None,
		# Money deposit
		'deposit': None
	}
	# By default simulation is on
	simulation = True

	def __init__(self, config, args = None):
		self.config = self.DEFAULT_CONFIG.copy()
		# Set the configuration
		self.config.update(config)
		# Set the exchange
		self.exchange = None
		# Set the order watchlist
		self.clearOrderList()
		# Clear the data
		self.data = {}
		self.updatePair({})
		# Set extra arguments if needed
		self.args = args

	def __str__(self):
		config = self.getConfig()
		bid = "None"
		if self.getBid() != None:
			bid = "%f" % self.getBid()
		ask = "None"
		if self.getAsk() != None:
			ask = "%f" % self.getAsk()
		#return "<%s/%s %s/%s>" % (str(self.getBaseCurrency()), str(self.getQuoteCurrency()), bid, ask)

		string_list = []
		string_list.append("%s/%s" % (bid, ask))
		for transactionType in ['sell', 'buy', 'transfer', 'withdraw', 'deposit']:
			if isinstance(self.getTransaction(transactionType), Transaction):
				string_list.append("%s(%s)" % (str(transactionType), str(self.getTransaction(transactionType))))
		return ("<%s/%s " % (str(self.getBaseCurrency()), str(self.getQuoteCurrency()))) + " ".join(string_list) + ">"

	def setExchange(self, exchange):
		"""
		Associate a pair with an exchange
		"""
		self.exchange = exchange

	def getExchange(self):
		"""
		Get the exchange associated with this pair
		"""
		return self.exchange

	def getOrderList(self):
		"""
		Returns the order list
		"""
		return self.orders

	def clearOrderList(self):
		"""
		Clear the order list
		"""
		self.orders = []

	def orderWatch(self, order):
		"""
		Add an order to the watchlist
		An order here will be executed as soon as the conditions are fulfilled
		"""
		self.orders.append(order)

	# Get the configuration
	def getConfig(self):
		return self.config

	# Get the arguments
	def getArgs(self):
		return self.args

	# Get the transactions
	def getTransaction(self, transactionType):
		config = self.getConfig()
		if config.has_key(transactionType):
			return self.getConfig()[transactionType]
		return None

	def getBaseCurrency(self):
		return self.getConfig()['baseCurrency']

	def getQuoteCurrency(self):
		return self.getConfig()['quoteCurrency']

	# Return the data
	def getSpread(self):
		"""
		Returns the spread
		"""
		return self.getAsk() - self.getBid()

	def getAsk(self):
		"""
		Returns the ask price
		"""
		return self.data['ask']

	def getBid(self):
		"""
		Returns the bid price
		"""
		return self.data['bid']

	def getAvg(self):
		"""
		Returns the average price
		"""
		return self.data['avg']

	def getVolume(self):
		return self.data['volume']

	def getVolumeCurrency(self):
		return self.data['volumeCurrency']

	def getTimestamp(self):
		"""
		Return the timestamp of the last updated data
		"""
		return self.data['timestamp']

	def orderBuy(self, rate = None, amount = None):
		"""
		Buy the base currency
		"""
		return OrderBuy(self, rate, amount)

	def orderSell(self, rate = None, amount = None):
		"""
		Sell the base currency
		"""
		return OrderSell(self, rate, amount)

	def updatePair(self, config):
		"""
		This function updates this exchange pair
		"""
		# Data from the stock exchange
		DEFAULT = {
			# Maximum Price
			'high': None,
			# Minimum Price
			'low': None,
			# Average Price
			'avg': None,
			# Trade Volume
			'volume': None,
			# Trade Volume in Currency
			'volumeCurrency': None,
			# Price of the last trade
			'last': None,
			# Bid Price
			'bid': None,
			# Ask Price
			'ask': None,
			# Timestamp
			'timestamp': None
		}
		self.data = DEFAULT.copy()
		self.data.update(config)

		# Process the orders if any
		orderList = self.getOrderList()
		self.clearOrderList()
		while orderList:
			order = orderList.pop()
			order.process()

class ExchangePairInverse(ExchangePair):
	"""
	An invert exchange pair is based on an existing pair
	"""
	def __init__(self, pair):
		self.pair = pair
		# Create a new config
		config = self.pair.getConfig()
		self.config = {
			'baseCurrency': config['quoteCurrency'],
			'quoteCurrency': config['baseCurrency'],
			'sell': config['sell'].clone().inverse(),
			'buy': config['buy'].clone().inverse(),
			'transfer': None,
			'withdraw': None,
			'deposit': None
		}
		# Set the order watchlist
		self.clearOrderList()

	def orderBuy(self, rate = None, amount = None):
		"""
		Buy the base currency
		"""
		return OrderSell(self.pair, rate, amount)

	def orderSell(self, rate = None, amount = None):
		"""
		Sell the base currency
		"""
		return OrderBuy(self.pair, rate, amount)

	def getOrderList(self):
		"""
		Returns the order list
		"""
		return self.pair.orders

	def clearOrderList(self):
		"""
		Clear the order list
		"""
		self.pair.orders = []

	def orderWatch(self, order):
		"""
		Add an order to the watchlist
		An order here will be executed as soon as the conditions are fulfilled
		"""
		self.pair.orders.append(order)

	def setExchange(self, exchange):
		"""
		Associate a pair with an exchange
		"""
		self.pair.exchange = exchange

	def getExchange(self):
		"""
		Get the exchange associated with this pair
		"""
		return self.pair.exchange

	def getAsk(self):
		"""
		Returns the ask price
		"""
		data = self.pair.data
		if data['bid'] == None:
			return None
		return 1. / data['bid']

	def getBid(self):
		"""
		Returns the bid price
		"""
		data = self.pair.data
		if data['ask'] == None:
			return None
		return 1. / data['ask']

	def getAvg(self):
		"""
		Returns the average price
		"""
		data = self.pair.data
		if data['avg'] == None:
			return None
		return 1. / self.pair.data['avg']

	def getTimestamp(self):
		"""
		Return the timestamp of the last updated data
		"""
		return self.pair.data['timestamp']

	def getVolume(self):
		return self.pair.data['volume']

	def getVolumeCurrency(self):
		return self.pair.data['volumeCurrency']

