#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.transaction import *
from exchanges.order import *
from exchanges.exchangepair import *
from utilz.log import *
from utilz.object import *

import json

class Exchange(object):
	"""
	This is a generic class to handle bitcoin stock exchanges
	"""
	# By default simulation is on
	simulation = True

	def __init__(self, config = {}):
		# Initialize the context
		self.context = {
			'name': None,
			'balance': {},
			'pairs': {},
			'orders': {},
			'timestamp': 0
		}
		# initialize the configuration
		self.config = {
			'recordWrite': None,
			'recordRead': None
		}
		self.config.update(config)
		# Initialize the exchange
		self.initialize()
		UtilzLog.info("Initialized exchange `%s' with currencies: %s." % (str(self.context['name']), ", ".join(self.currencyList())) , 1)
		# If record read is set, open the target file
		if isinstance(self.config['recordRead'], str):
			self.context['recordFile'] = open(self.config['recordRead'])
			if self.simulation == False:
				raise error("This exchange `%s' cannot be in non-simulation mode while reading records" % (str(self.context['name'])))
		# If record write is set, clear the file if it exists
		if isinstance(self.config['recordWrite'], str):
			open(self.config['recordWrite'], 'w').close()
			UtilzLog.info("Recording exchange `%s' to `%s'." % (str(self.context['name']), self.config['recordWrite']) , 1)

	def __str__(self):
		string_list = []
		for baseCurrency in self.context['pairs']:
			for quoteCurrency in self.context['pairs'][baseCurrency]:
				ex = self.context['pairs'][baseCurrency][quoteCurrency]
				string_list.append(str(ex))
		return ("[Exchange:%s\n" % (self.context['name'])) + "\n".join(string_list) + "]"

	@staticmethod
	def disableSimulationMode():
		"""
		This function sets the simulation mode to all sub identities
		"""
		Exchange.simulation = False
		ExchangePair.simulation = False
		Order.simulation = False
		Transaction.simulation = False

	def createOrder(self, pair, transactionType, rate, amount):
		"""
		Creates an order
		"""
		if transactionType == "sell":
			return OrderSell(pair, rate, amount)
		else:
			return OrderBuy(pair, 1. / rate, amount * rate)

	def setTimestamp(self, timestamp):
		"""
		Update the time base of this exchange
		"""
		self.context['timestamp'] = timestamp

	def getTimestamp(self):
		"""
		Return the timestamp of this exchange
		"""
		return self.context['timestamp']

	def printBalance(self):
		"""
		Print the view of the current balance
		"""
		balance = self.getBalance()
		currencyList = self.currencyList()
		stringList = []
		balancePlaced = self.getPlacedBalance()
		for currency in currencyList:
			amount = 0.
			if balance.has_key(currency):
				amount = balance[currency]
			string = "%s:\t%f" % (currency, amount)
			if balancePlaced.has_key(currency):
				string = "%s\t(+%f)" % (string, balancePlaced[currency])
			stringList.append(string)
		return "\n".join(stringList)

	def initialize(self):
		"""
		Initialize the context of the exchange
		"""
		raise error("The `initialize' function is missing for this exchange.")

	def updatePairsPort(self):
		"""
		Update the rates of the exchange
		This function must be implemenent by the exchange port
		"""
		raise error("The `updatePairsPort' function is missing for this exchange.")

	def updateBalancePort(self):
		"""
		Update the balance of the exchange
		This function must be implemenent by the exchange port
		"""
		raise error("The `updateBalancePort' function is missing for this exchange.")

	def updateBalance(self):
		"""
		Updates the balance
		"""
		if self.simulation == False:
			self.updateBalancePort()

	def updatePairs(self):
		"""
		Update the rates of the exchange
		Return True if there is more pairs to update.
		False if nothing left.
		"""
		# To read the records from a file
		if isinstance(self.config['recordRead'], str):
			result = self.recordReadPairs()
		else:
			result = self.updatePairsPort()
		# To write the records
		if isinstance(self.config['recordWrite'], str):
			self.recordWritePairs()
		# Return the result
		return False if result == False else True

	def recordWritePairs(self):
		"""
		This function will record the exchange data
		"""
		dataPairs = []
		# Create the previous data pair if it is the first time
		if not hasattr(self, 'prevDataPairs'):
			self.prevDataPairs = {}
		# Build the data
		for baseCurrency in self.context['pairs']:
			for quoteCurrency in self.context['pairs'][baseCurrency]:
				pair = self.context['pairs'][baseCurrency][quoteCurrency]
				# Discard inverted pairs
				if isinstance(pair, ExchangePairInverse):
					continue
				# Create the data
				data = {
					'b': baseCurrency,
					'q': quoteCurrency,
					'bid': pair.getBid(),
					'ask': pair.getAsk(),
					'avg': pair.getAvg(),
					'v': pair.getVolume(),
					't': pair.getTimestamp()
				}
				# Pair key
				key = str(baseCurrency) + str(quoteCurrency)
				# Remove previous data
				if not self.prevDataPairs.has_key(key):
					self.prevDataPairs[key] = data
				else:
					# Check if any of the other values have changed, if yes, remove it
					if self.prevDataPairs[key]['bid'] == data['bid']:
						del data['bid']
					if self.prevDataPairs[key]['ask'] == data['ask']:
						del data['ask']
					if self.prevDataPairs[key]['avg'] == data['avg']:
						del data['avg']
					if self.prevDataPairs[key]['v'] == data['v']:
						del data['v']
					if self.prevDataPairs[key]['t'] == data['t']:
						del data['t']
					self.prevDataPairs[key].update(data)
				# Add it to the main stucture only if there is more info than only the currencies
				if len(data) > 2:
					dataPairs.append(data)
		# Write changes all the time (even if nothing has changed) to make sure the frequency of the update is identical as when it has been captured.
		# Save the data to a file
		dataPairs = json.dumps(dataPairs, separators = (',', ':'))
		with open(self.config['recordWrite'], "a") as f:
			f.write(dataPairs + "\n")
			f.close()

	def recordReadPairs(self):
		"""
		This function will read the records and updates the paris
		"""
		# Make sure the file instance is correct
		if not self.context.has_key('recordFile') or not isinstance(self.context['recordFile'], file):
			raise error("The file context is not set or invalid, please double check.")
		content = self.context['recordFile'].readline()
		# If this is the end of the file
		if content == "":
			UtilzLog.error("You have reached the end of the record.")
			return False
		pairDataList = json.loads(content)
		# Create the previous data pair if it is the first time
		if not hasattr(self, 'prevDataPairs'):
			self.prevDataPairs = {}

		# Update all the pairs
		for pairData in pairDataList:
			# Make sure the minimal arguments are set
			if not pairData.has_key('b') or not pairData.has_key('q'):
				raise error("the currencies are missing in this record: `%s'." % (str(pairData)))
			# Build the pair key
			key = str(pairData['b']) + str(pairData['q'])
			# Check if this is the first time
			if not self.prevDataPairs.has_key(key):
				self.prevDataPairs[key] = pairData
			else:
				self.prevDataPairs[key].update(pairData)
			# Make sure all the arguments are set
			if not self.prevDataPairs[key].has_key('bid') or not self.prevDataPairs[key].has_key('ask') or not self.prevDataPairs[key].has_key('avg') or not self.prevDataPairs[key].has_key('v') or not self.prevDataPairs[key].has_key('t'):
				raise error("The currencies are missing in this record: `%s'." % (str(self.prevDataPairs[key])))

		# Timestamp is unset
		timestamp = None
		# Loop through the pair data
		for key in self.prevDataPairs:
			# Update the pair
			self.pairUpdate(self.prevDataPairs[key]['b'], self.prevDataPairs[key]['q'], {
				'bid': self.prevDataPairs[key]['bid'],
				'ask': self.prevDataPairs[key]['ask'],
				'avg': self.prevDataPairs[key]['avg'],
				'volume': self.prevDataPairs[key]['v'],
				'timestamp': self.prevDataPairs[key]['t']
			})
			# Update the timestamp
			timestamp = self.prevDataPairs[key]['t']

		# Update the timestamp of the exchange
		if timestamp != None:
			self.setTimestamp(timestamp)

	def updateOrders(self):
		"""
		This function updates the orders
		"""
		if self.simulation == True:

			timestamp = self.getTimestamp()
			# Get the order ID list
			orderIDList = [i for i in self.context['orders']]

			# Loop through the orders
			for identifier in orderIDList:

				# Read the order
				o = self.context['orders'][identifier]
				order = o['order']
				time = timestamp - o['timestamp']

				# Get through the state machine
				if order.getStatus() == Order.STATUS_PLACED:
					# Check if it is considered effective
					if time >= o['transaction'].getTimeEffective():
						# Get the order info
						info = order.getInfo()
						# Make sure the rate is still ok
						if info['rate'] > order.getUpdatedRate(info['pair']):
							self.orderCanceled(identifier, "The rate of this order has decreased from `%f' to `%f'" % (info['rate'], order.getUpdatedRate(info['pair'])))
						else:
							self.orderEffective(identifier)

				elif order.getStatus() == Order.STATUS_EFFECTIVE:

					if time >= o['transaction'].getTimeEffective() + o['transaction'].getTimeCompleted():
						# Set this order as completed
						self.orderCompleted(identifier)

		else:
			result = self.updateOrdersPort()
			if result[0] == True:
				# Retrieve the active order list
				activeOrders = result[1]

				# Make sure this list has been set
				if not isinstance(activeOrders, dict):
					raise error("This function must return the current active order list, it returned instead `%s'" % (activeOrders))

				# Loop through all the known orders
				for identifier in self.context['orders']:
					# The current order
					o = self.context['orders'][identifier]
					# This order is also part of the active order list
					if identifier in activeOrders:
						# Check its status
						if activeOrders[identifier]['status'] == Order.STATUS_COMPLETED:
							self.orderCompleted(identifier)
						elif activeOrders[identifier]['status'] == Order.STATUS_EFFECTIVE:
							self.orderEffective(identifier)
						elif activeOrders[identifier]['status'] == Order.STATUS_PLACED:
							pass # Do nothing, keep monitoring
						else:
							raise error("Unknown order status `%s'" % (str(activeOrders[identifier])))
						# Remove this order from the list
						del activeOrders[identifier]
					# If this order is not part of the active list
					else:
						# If is currently in placed state, set it to completed
						if o['order'].getStatus() == Order.STATUS_PLACED:
							self.orderCompleted(identifier)

				# If there are order that are not known, create and add them
				for identifier in activeOrders:
					if not activeOrders[identifier]["type"] or not activeOrders[identifier]["pair"] or not activeOrders[identifier]["rate"] or not activeOrders[identifier]["amount"]:
						raise error("This order `%s' is missing `type', `pair', `rate' and/or `amount' attributes" % (str(ctiveOrders[identifier])))
					# Identify the pair
					pair = self.getPair(activeOrders[identifier]["pair"][0], activeOrders[identifier]["pair"][1])
					# Create the order
					order = self.createOrder(pair, activeOrders[identifier]["type"], activeOrders[identifier]["rate"], activeOrders[identifier]["amount"])
					# Force the placed status
					order.status = Order.STATUS_PLACED
					# Make this order active
					order.active()
					# Watch this order from now on
					self.orderWatch(identifier, order)

	def updateOrdersPort(self):
		"""
		This funciton update the status of the placed orders
		"""
		raise error("The `updateOrdersPort' function must be implemented.")

	def trade(self, order):
		"""
		This function will place an order.
		Returns True in case of success, False otherwise.
		"""
		# Get the order info
		info = order.getInfo()
		# Get the orginal currency
		amountCurrency = order.getAmountCurrency()

		if self.simulation == True:
			# Make sure there is enough money in the balance
			balance = self.getBalance(amountCurrency)
			if info['amount'] > balance:
				return [False, "Un-sufficient balance (available: %f %s, needed: %f %s)" % (balance, amountCurrency, info['amount'], amountCurrency)]
			# Make sure the order is within the limits
			result = info['transaction'].withinLimits(info['rate'], info['amount'])
			if result[0] == False:
				return [False, result[1]]
			# Create an ID for this transaction
			orderId = order.getId()

		# Process the order
		else:
			result = self.tradePort(order)
			if result[0] == False:
				return result
			orderId = result[1]

		# Subtract the money from the balance
		self.addBalance(-info['amount'], amountCurrency)

		# Set the order into the exchange watchlist
		self.orderWatch(orderId, order)

		# Success
		return [True]

	def tradePort(self, order):
		"""
		This function is the port of the exchange trade.
		Returns a list with 2 arguments. the first argument is a boolean
		defining the status of the order (true for success, False for error).
		The second argument in case of an error is an error message, in case of
		a success, it is the order ID.
		"""
		raise error("The `tradePort' function must be implemented.")

	def getName(self):
		"""
		Get the exchange name
		"""
		return self.context['name']

	def addBalance(self, balance, currency = None):
		"""
		Update the current balance on the wallet of this exchange.
		This should not be used unless it is for simulation.
		If currency is set, update only the balance of this specific currency
		"""
		if currency == None:
			for c in balance:
				if not self.context['balance'].has_key(c):
					self.context['balance'][c] = 0.
				self.context['balance'][c] = self.context['balance'][c] + balance[c]
		else:
			if not self.context['balance'].has_key(currency):
				self.context['balance'][currency] = 0.
			self.context['balance'][currency] = self.context['balance'][currency] + balance

	def setBalance(self, balance, currency = None):
		"""
		Set the current balance on the wallet of this exchange.
		This should not be used unless it is for simulation.
		If currency is set, set only the balance of this specific currency
		"""
		# The assignment is atomic with python, so this function is thread safe
		if currency == None:
			self.context['balance'] = balance
		else:
			self.context['balance'][currency] = balance

	def getBalance(self, currency = None):
		"""
		Return the current balance of this exchange
		If currency is set, returns the balance of this specific currency
		"""
		if currency == None:
			return self.context['balance']
		if self.context['balance'].has_key(currency):
			return self.context['balance'][currency]
		return 0.

	def getPlacedBalance(self, currency = None):
		"""
		Return the money in transition, money currenlty frozen for the transaction
		If currency is set, returns the balance of this specific currency
		"""
		orderList = self.getOrders()
		balance = {}
		for order in orderList:
			c = order.getAmountCurrency()
			if not balance.has_key(c):
				balance[c] = 0.
			balance[c] = balance[c] + order.getAmount()
		# Return the balance
		if currency == None:
			return balance
		if balance.has_key(currency):
			return balance[currency]
		return 0.

	def getTotalBalance(self, currency = None):
		"""
		Return the total balance of this exchange
		If currency is set, returns the balance of this specific currency
		"""
		if currency == None:
			balance = self.getBalance()
			balancePlaced = self.getPlacedBalance()
			for c in balance:
				if balancePlaced.has_key(c):
					balancePlaced[c] = balancePlaced[c] + balance[c]
				else:
					balancePlaced[c] = balance[c]
			return balancePlaced
		return self.getBalance(currency) + self.getPlacedBalance(currency)

	def getOrders(self):
		"""
		Returns the list of active orders
		"""
		return [self.context['orders'][i]['order'] for i in self.context['orders']]

	def currencyList(self):
		"""
		List all available currencies in this exchange
		"""
		return list(set([x for x in self.context['pairs']]))

	def getPair(self, baseCurrency, quoteCurrency = None):
		"""
		Returns the pair(s) based on the specified currency(ies)
		If only one argument is passed into argument, returns a dictionary with the pairs
		If 2 currencies are passed, return the pair
		"""
		if not self.context['pairs'].has_key(baseCurrency):
			return {} if quoteCurrency == None else None
		if quoteCurrency == None:
			return self.context['pairs'][baseCurrency]
		if not self.context['pairs'][baseCurrency].has_key(quoteCurrency):
			return None
		return self.context['pairs'][baseCurrency][quoteCurrency]

	def pairAdd(self, pair):
		"""
		This function adds a new pair to the exchange market
		\param pair The new pair to add
		"""
		# Make sure the pair has the currencies
		baseCurrency = pair.getBaseCurrency()
		quoteCurrency = pair.getQuoteCurrency()
		if baseCurrency == None or quoteCurrency == None:
			raise error("This pair is incomplete `%s'." % (str(pair)))

		if not self.context['pairs'].has_key(baseCurrency):
			self.context['pairs'][baseCurrency] = {}
		if self.context['pairs'][baseCurrency].has_key(quoteCurrency):
			raise error("This pair already exists `%s/%s'." % (str(baseCurrency), str(quoteCurrency)))
		self.context['pairs'][baseCurrency][quoteCurrency] = pair
		# Associate this pari with this exchange
		pair.setExchange(self)
		# Add the inverse pair if none is existing
		if not self.context['pairs'].has_key(quoteCurrency):
			self.context['pairs'][quoteCurrency] = {}
		if not self.context['pairs'][quoteCurrency].has_key(baseCurrency):
			self.context['pairs'][quoteCurrency][baseCurrency] = ExchangePairInverse(pair)

	def pairUpdate(self, baseCurrency, quoteCurrency, data):
		"""
		This function updates a specific exchange pair
		"""
		# Make sure the pair exists
		if not self.context['pairs'].has_key(baseCurrency) or not self.context['pairs'][baseCurrency].has_key(quoteCurrency) or not isinstance(self.context['pairs'][baseCurrency][quoteCurrency], ExchangePair):
			raise error("This exchange does not have the following pair `%s/%s'." % (str(baseCurrency), str(quoteCurrency)))
		self.context['pairs'][baseCurrency][quoteCurrency].updatePair(data)

	def orderWatch(self, identifier, order):
		"""
		Add an order to the watch list
		"""
		# Make sure this order is complete
		info = order.getInfo(strict = True)
		self.context['orders'][identifier] = {
			'order': order,
			'transaction': info['transaction'],
			'timestamp': self.getTimestamp()
		}

	def orderStopWatch(self, identifier):
		"""
		Remove an order from the watch list and returns it
		"""
		if not self.context['orders'].has_key(identifier):
			raise error("This order `%s' has no entry." % (str(identifier)))
		# Find the order
		o = self.context['orders'][identifier]
		# Remove it from the list
		del self.context['orders'][identifier]
		# Return the order
		return o

	def orderEffective(self, identifier):
		"""
		Set the order as effective
		"""
		if not self.context['orders'].has_key(identifier):
			raise error("This order `%s' has no entry." % (str(identifier)))
		# Find the order
		o = self.context['orders'][identifier]
		# Udpate the status
		o['order'].setStatus(Order.STATUS_EFFECTIVE)

	def orderCanceled(self, identifier, message = ""):
		"""
		Remove an order from the watch list
		"""
		# Stop watching this order
		o = self.orderStopWatch(identifier)
		# Re-fill the balance
		self.addBalance(o['order'].getAmount(), o['order'].getAmountCurrency())
		# Set it as completed
		o['order'].setStatus(Order.STATUS_CANCELED, message)

	def orderCompleted(self, identifier):
		"""
		Remove an order from the watch list
		"""
		# Stop watching this order
		o = self.orderStopWatch(identifier)
		# Set the new balance
		self.addBalance(o['order'].estimate(), o['order'].getFinalCurrency())
		# Set it as completed
		o['order'].setStatus(Order.STATUS_COMPLETED)
