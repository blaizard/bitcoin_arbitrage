#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.transaction import *
from utilz.log import *
from utilz.object import *

import sys
import math

class Order(object):
	"""
	Defines an order.

	An order defines a transaction from a pair baseCurrency/quoteCurrency.
	There are multiple type of transactions:
	- 'buy' = BUY baseCurrency = quoteCurrency => 1 / rate * baseCurrency
	- 'sell' = SELL baseCurrency = baseCurrency => rate * quoteCurrency

	Here is the definition of the various terms used:
		- rate: this is the rate of the transaction.
		- amount: the number of the initial currency to trade
	"""
	# By default simulation is on
	simulation = True
	# List of active orders
	activeList = []
	# Uinque ID seed
	uniqueIdSeed = 0

	ESTIMATE_FEE = 0
	ESTIMATE_NO_FEE = 1
	ESTIMATE_INVERSE = 2
	# Update specific
	UPDATE_NORMAL = 0
	UPDATE_FROM_AVERAGE = 1
	# Order statuses
	STATUS_IDLE = "idle"
	STATUS_PENDING = "pending"
	STATUS_PLACED = "placed"
	STATUS_EFFECTIVE = "effective"
	STATUS_COMPLETED = "completed"
	STATUS_CANCELED = "canceled"

	def __init__(self, pair, transactionType, rate = None, amount = None, conditions = {}):
		"""
		This function creates an order object
		"""
		self.pair = pair
		self.transactionType = transactionType
		if rate == None:
			self.rate = None
		else:
			self.setRate(rate)
		if amount == None:
			self.amount = None
		else:
			self.setAmount(amount)
		self.status = Order.STATUS_IDLE
		self.chain = []
		self.statusMessage = ""
		self.orderId = Order.getUniqueId()
		# Add the conditions
		defaultConditions = {
			'minTimestamp': -1,
			'maxTimestamp': sys.maxint,
			# Infinte timeout, if none -1, it will overwrite 'maxTimestamp'
			'timeout': -1,
			'minRate': -1,
			'maxRate': sys.maxint
		}
		self.conditions = defaultConditions.copy()
		self.conditions.update(conditions)

	def __str__(self):
		"""
		Print an order
		"""
		stringList = []
		order = self
		while order:
			stringList.append(order.printOrder())
			order = order.next()
		return " -> ".join(stringList)

	@staticmethod
	def getUniqueId():
		"""
		This function generates a unique ID and returns it
		"""
		Order.uniqueIdSeed = Order.uniqueIdSeed + 1
		return Order.uniqueIdSeed

	@staticmethod
	def getActiveList():
		"""
		Returns the list of active orders.
		Active orders are otherders that are processing.
		"""
		return Order.activeList

	@staticmethod
	def getPlacedList():
		"""
		Returns the list of placed orders.
		it can be either placed orders, effective orders or completed orders.
		"""
		return [o for o in Order.activeList if o.getStatus() == STATUS_PLACED or o.getStatus() == STATUS_EFFECTIVE  or o.getStatus() == STATUS_COMPLETED]

	def printOrder(self):
		"""
		Print the current order
		"""
		conditions = ""
		# Describes conditions if any
		if self.status == Order.STATUS_IDLE or self.status == Order.STATUS_PENDING:
			conditionsList = []
			if self.conditions['minTimestamp'] != -1:
				conditionsList.append("minTimestamp=%i" % (self.conditions['minTimestamp']))
			if self.conditions['maxTimestamp'] != sys.maxint:
				conditionsList.append("maxTimestamp=%i" % (self.conditions['maxTimestamp']))
			if self.conditions['timeout'] != -1:
				conditionsList.append("timeout=%i" % (self.conditions['timeout']))
			if self.conditions['minRate'] != -1:
				conditionsList.append("minRate=%f" % (self.conditions['minRate']))
			if self.conditions['maxRate'] != sys.maxint:
				conditionsList.append("maxRate=%f" % (self.conditions['maxRate']))
			conditions = " condition(s):%s" % (";".join(conditionsList))

		return "<%s %s/%s rate:%s amount:%s%s>" % (str(self.transactionType), str(self.pair.getBaseCurrency()), str(self.pair.getQuoteCurrency()), str(self.rate), str(self.amount), conditions)

	def printEstimate(self, amount = 1.):
		"""
		Print an estimate of an order
		"""
		stringList = []
		stringList.append("%f %s" % (amount, str(self.getAmountCurrency())))
		order = self
		while order:
			amount = order.estimate(amount)
			stringList.append("%f %s" % (amount, str(order.getFinalCurrency())))
			order = order.next()
		return " -> ".join(stringList)

	def clone(self, order = None):
		"""
		Clone this order
		"""
		if order == None:
			order = Order(self.pair, self.transactionType, self.rate, self.amount)
		# Copy the order status
		order.status = self.status
		# Copy the conditions
		order.conditions = self.conditions.copy()
		# Create a new ID
		order.orderId = Order.getUniqueId()
		# Do not clone the chaine
		order.chain = []
		return order

	def cloneChain(self, order = None):
		"""
		Clone an order with its chain
		"""
		order = self.clone(order)
		# Clone the chain
		for o in self.chain:
			order.chain.append(o.cloneChain())
		return order

	def getId(self):
		"""
		Return the unique order ID
		"""
		return self.orderId

	def getAmountCurrency(self):
		"""
		Get the currency of the amount of this order
		"""
		raise error("This function `getAmountCurrency' must be created.")

	def getFinalCurrency(self):
		"""
		Get the currency of the final amount of this order
		"""
		raise error("This function `getFinalCurrency' must be created.")

	def update(self, mode = UPDATE_NORMAL):
		"""
		Update the rate of this order
		"""
		pair = self.getPair()
		if pair == None:
			raise error("This order is incomplete `%s'." % (str(self)))
		self.rate = self.getUpdatedRate(pair, mode)
		# Make it chainable
		return self

	def updateChain(self, mode = UPDATE_NORMAL):
		"""
		Update all the orders
		"""
		order = self
		while order:
			order.update(mode)
			order = order.next()
		# Make it chainable
		return self

	def next(self, index = 0):
		"""
		Return the next order associated with this one
		"""
		if index >= len(self.chain):
			return None
		return self.chain[index]

	def addChainOrder(self, order, conditions = {}):
		"""
		Add a consecutive order the end of the chain list
		"""
		o = self
		while o:
			if o.next() == None:
				o.chain.append(order)
				break
			o = o.next()

	def getType(self):
		"""
		Returns the transaction type
		"""
		return self.transactionType

	def getAmount(self):
		"""
		Returns the order amount
		"""
		return self.amount

	def getTransaction(self):
		"""
		Retruns the transaction associated with this order
		"""
		pair = self.getPair()
		transactionType = self.getType()
		return pair.getTransaction(transactionType)

	def getMaxDecimal(self):
		"""
		Get the maximum number of decimals allowed for this order
		"""
		return self.getTransaction().getMaxDecimal()

	def floor(self, n):
		"""
		Floor a number down to the number of digits allowed by this transaction
		"""
		d = self.getMaxDecimal()
		powd = math.pow(10, d)
		return int(n * powd) * 1. / powd

	def setAmount(self, amount):
		"""
		Set the order amount
		"""
		self.amount = self.floor(amount)

	def getRate(self):
		"""
		Returns the rate
		"""
		return self.rate

	def getRateChain(self):
		"""
		Return a list containing all the rates from the chain
		"""
		o = self
		rateList = []
		while o:
			rateList.append(o.getRate())
			o = o.next()
		return rateList

	def setRate(self, rate):
		"""
		Set the rate of the order
		"""
		self.rate = self.floor(rate)

	def getPair(self):
		"""
		Returns the associated pair (optional)
		"""
		return self.pair

	def getStatus(self):
		"""
		Return the current status of the order
		"""
		return self.status

	def getMessage(self):
		"""
		Return the status message if any
		"""
		return self.statusMessage

	def setStatus(self, status, message = ""):
		"""
		Set the current status of the order
		"""
		self.status = status
		self.statusMessage = message
		# Process with the new status
		self.process()

	def getBaseCurrency(self):
		"""
		Return the initial currency of the order
		"""
		return self.pair.getBaseCurrency()

	def getQuoteCurrency(self):
		"""
		Return the final currency of the order
		"""
		return self.pair.getQuoteCurrency()

	def isValid(self, amount = None):
		"""
		Check if this order is valid or not
		"""
		# Get the order info
		info = self.getInfo(amount, False)
		if info == None:
			return False
		# Check if this order is within the limits
		if transaction.withinLimits(info['rate'], info['amount']) == False:
			return False
		return True

	def getInfo(self, amount = None, strict = True):
		"""
		Helper function, to check and get the order amount
		"""
		pair = self.getPair()
		rate = self.getRate()
		# If the amount is not set, use the one from the order
		if amount == None:
			amount = self.getAmount()
		else:
			amount = self.floor(amount)
		transactionType = self.getType()
		transaction = pair.getTransaction(transactionType)
		# Make sure none of these are undefined
		if pair == None or rate == None or amount == None or transactionType == None or transaction == None:
			if strict:
				raise error("This order is incomplete `%s'." % (str(self)))
			else:
				return None
		return {'status': self.getStatus(), 'pair': pair, 'rate': rate, 'amount': amount, 'type': transactionType, 'transaction': transaction}

	def testConditions(self):
		"""
		Test the order conditions, if all conditions are passing, returns True
		otherwise False if this order should be kept or None if it should be
		deleted
		"""
		pair = self.getPair()
		# Timestamp
		timestamp = pair.getTimestamp()
		if timestamp < self.conditions['minTimestamp']:
			return [False]
		if timestamp > self.conditions['maxTimestamp']:
			return [None, "Order exceeded its timeout"]
		# Rate
		rate = self.getUpdatedRate(pair)
		if rate < self.conditions['minRate']:
			return [False]
		if rate > self.conditions['maxRate']:
			return [False]
		# Make sure the exchange has enough balance
		exchange = pair.getExchange()
		amountCurrency = self.getAmountCurrency()
		balance = exchange.getBalance(amountCurrency)
		amount = self.getAmount()
		if balance < amount:
			return [None, "Not enough balance (%f %s needed, %f %s left)" % (balance, amountCurrency, amount, amountCurrency)]

		return [True]

	def getConditions(self, condition = None):
		"""
		Return the order conditions
		"""
		if condition == None:
			return self.conditions
		return self.conditions[condition]

	def setConditions(self, value, condition = None):
		"""
		Return the order conditions
		"""
		if condition == None:
			self.conditions = value
		else:
			self.conditions[condition] = value

	def estimate(self, amount = None, mode = ESTIMATE_FEE):
		"""
		Estimates the final cost of an order
		"""
		# Get the order info
		info = self.getInfo(amount)
		# Calculate the final amount of curency2 after the order
		if mode & Order.ESTIMATE_INVERSE:
			finalAmount = (1. / info['rate']) * info['amount']
		else:
			finalAmount = info['rate'] * info['amount']
		# Calculate the transaction fee if any
		if mode & Order.ESTIMATE_NO_FEE:
			transactionFee = 0.
		else:
			transactionFee = info['transaction'].getFee(finalAmount)
		# The final amount
		finalAmount = finalAmount - transactionFee
		return self.floor(finalAmount)

	def estimateChain(self, amount = None, mode = ESTIMATE_FEE):
		"""
		Estimates the final cost of an order chain
		"""
		order = self
		while order:
			amount = order.estimate(amount, mode)
			order = order.next()
		return amount

	def execute(self, amount = None):
		"""
		Execute an order.
		Here is the lifetime of an order:
		Execute -> Pending -> Placed -> Effective -> Completed
		"""
		# Get the order info
		info = self.getInfo(amount)
		# Make sure the current status is pending
		if self.status != Order.STATUS_IDLE:
			raise error("The status of this transaction is `%s', it should be `%s'." % (self.getStatus(), Order.STATUS_IDLE))
		# Get the exchange associated with this pair
		exchange = info['pair'].getExchange()

		# Clone the order
		order = self.cloneChain()

		# Set an amount to this order
		order.setAmount(info['amount'])

		# Simulation, adds some specific conditions
		if self.simulation:
			# Add a timeout of 10s
			#timeout = order.getConditions('timeout')
			#timeout = max(timeout, 10)
			#order.setConditions(timeout, 'timeout')
			# Adjust this order with the highest up-to-date rate
			r = order.getConditions('minRate')
			r = max(r, info['rate'])
			order.setConditions(r, 'minRate')

		# Start the timer for the timeout
		timeout = order.getConditions('timeout')
		if timeout > 0:
			order.setConditions(timeout + info['pair'].getTimestamp(), 'maxTimestamp')

		# Add this order to the active order list
		order.active()

		# This order is in pending state
		UtilzLog.order("[PENDING] [ID=%i] t=`%s' %s" % (order.getId(), str(info['pair'].getTimestamp()), str(order)))

		# Set this order as pending
		order.setStatus(Order.STATUS_PENDING)

	def process(self):
		"""
		Process the order
		"""
		# Get the order info
		info = self.getInfo()
		# Order processing state machine
		if info['status'] == Order.STATUS_PENDING:
			"""
			This is the very first state, before the order has been placed.
			This state has the role to place the order
			"""
			# Check the conditions, if False push it back to the pair watchlist
			matchConditions = self.testConditions()

			# Put back the order into the watchlist
			if matchConditions[0] == False:
				info['pair'].orderWatch(self)
				return

			# Removed this order
			elif matchConditions[0] == None:
				# Cancel the order
				self.setStatus(Order.STATUS_CANCELED, matchConditions[1])
				return

			# Place the order
			self.setStatus(Order.STATUS_PLACED)

		elif info['status'] == Order.STATUS_PLACED:
			UtilzLog.order("[PLACED] [ID=%i] t=`%s' %s" % (self.getId(), str(info['pair'].getTimestamp()), str(self)))

			# Identify the exchange
			exchange = info['pair'].getExchange()

			# Adjust this order with the highest rate
			rate = max(self.getUpdatedRate(info['pair']), info['rate'])
			self.setRate(rate)

			# Place the order
			result = exchange.trade(self)

			# If this order did not pass through
			if result[0] == False:
				self.setStatus(Order.STATUS_CANCELED, result[1])
				return

		elif info['status'] == Order.STATUS_EFFECTIVE:
			UtilzLog.order("[EFFECTIVE] [ID=%i] t=`%s' %s" % (self.getId(), str(info['pair'].getTimestamp()), str(self)))

		elif info['status'] == Order.STATUS_CANCELED:
			# Cancel message
			UtilzLog.error("[CANCELED] [ID=%i] t=`%s' %s (%s)" % (self.getId(), str(info['pair'].getTimestamp()), str(self), self.getMessage()))
			# Set this order as unactive
			self.unactive()
			return

		elif info['status'] == Order.STATUS_COMPLETED:
			# Completed message
			UtilzLog.order("[COMPLETED] [ID=%i] t=`%s' %s" % (self.getId(), str(info['pair'].getTimestamp()), str(self)))
			# Set this order as unactive
			self.unactive()
			# Execute the next chained orders if any
			index = 0
			while self.next(index):
				self.next(index).execute(self.estimate())
				index = index + 1
			return

		else:
			raise error("The state `%s' is not allowed for this order." % (info['status']))

	def active(self):
		"""
		Set the order to the active order list.
		"""
		Order.activeList.append(self)

	def unactive(self):
		"""
		Remove the order to the active order list.
		"""
		# Remove it from the active order list
		while self in Order.activeList:
			Order.activeList.remove(self)

class OrderBuy(Order):
	"""
	Buy Order
	- 'buy': quoteCurrency * rate => baseCurrency
	"""
	def __init__(self, pair, rate = None, amount = None):
		super(OrderBuy, self).__init__(pair, "buy", rate, amount)

	def clone(self, order = None):
		"""
		Clone this order
		"""
		if order == None:
			order = OrderBuy(self.pair, self.rate, self.amount)
		return super(OrderBuy, self).clone(order)

	def cloneInverse(self):
		"""
		Clone and invert this order
		"""
		order = OrderSell(self.pair, self.rate, self.amount)
		return self.clone(order)

	def getUpdatedRate(self, pair, mode = Order.UPDATE_NORMAL):
		"""
		Returns the updated rate of the order taken from the pair
		"""
		if mode == Order.UPDATE_FROM_AVERAGE:
			return 1. / pair.getAvg()
		return 1. / pair.getAsk()

	def getAmountCurrency(self):
		"""
		Get the currency of the amount of this order
		"""
		pair = self.getPair()
		# Make sure none of these are not defined
		if pair == None:
			raise error("This order is incomplete `%s'." % (str(self)))
		return pair.getQuoteCurrency()

	def getFinalCurrency(self):
		"""
		Get the currency of the final amount of this order
		"""
		pair = self.getPair()
		# Make sure none of these are not defined
		if pair == None:
			raise error("This order is incomplete `%s'." % (str(self)))
		return pair.getBaseCurrency()

class OrderSell(Order):
	"""
	Sell order
	- 'sell': baseCurrency * rate => quoteCurrency
	"""
	def __init__(self, pair, rate = None, amount = None):
		super(OrderSell, self).__init__(pair, "sell", rate, amount)

	def clone(self, order = None):
		"""
		Clone this order
		"""
		if order == None:
			order = OrderSell(self.pair, self.rate, self.amount)
		return super(OrderSell, self).clone(order)

	def cloneInverse(self):
		"""
		Clone and invert this order
		"""
		order = OrderBuy(self.pair, self.rate, self.amount)
		return self.clone(order)

	def getUpdatedRate(self, pair, mode = Order.UPDATE_NORMAL):
		"""
		Returns the updated rate of the order taken from the pair
		"""
		if mode == Order.UPDATE_FROM_AVERAGE:
			return pair.getAvg()
		return pair.getBid()
			

	def getAmountCurrency(self):
		"""
		Get the currency of the amount of this order
		"""
		pair = self.getPair()
		# Make sure none of these are not defined
		if pair == None:
			raise error("This order is incomplete `%s'." % (str(self)))
		return pair.getBaseCurrency()

	def getFinalCurrency(self):
		"""
		Get the currency of the final amount of this order
		"""
		pair = self.getPair()
		# Make sure none of these are not defined
		if pair == None:
			raise error("This order is incomplete `%s'." % (str(self)))
		return pair.getQuoteCurrency()


