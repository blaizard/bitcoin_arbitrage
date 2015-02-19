#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.exchange import *
from exchanges.order import *
from utilz.object import *
from utilz.log import *

class triangularArbitrage(object):
	"""
	This algorithm implements triabngular arbitrage and identifies benefical transactions
	"""
	MIN_DEPTH = 3 # Minimal number of transactions
	MAX_DEPTH = 3 # Maximal number of transactions

	# The minimal gain (in percent) in the triangular arbitrage from which
	# an opportunity should be considered
	GAIN_THRESHOLD_PERCENT = 0
	# The maximum timestamp spread to asses that data are still valid
	# Any timestamp spread greater than this will be ignored
	MAX_TIMESTAMP_SPREAD = 2.

	# Timeout until an order is valid
	ORDER_TIMEOUT = 10

	def __init__(self, exchange):
		# Save the exchange for future use
		self.x = exchange
		# Identify all possible transactions
		self.transactions = {}
		stringList = []
		for currency in self.x.currencyList():
			self.transactions[currency] = self.identifyTransactions(currency)
			stringList.append("%s: %i" % (currency, len(self.transactions[currency])))
		UtilzLog.info("Transaction identified: %s" % (", ".join(stringList)), 1)
		# Create chain orders from the triangular transactions identified
		self.createChainOrders(self.transactions)
		UtilzLog.info("Initialized triangular arbitrage algorithm", 3)

	def preprocess(self, initialAmount = 1.):
		"""
		Pre-process the algorithm
		"""
		self.opportunityList = {}

		# Monitor all currencies, we must to it to ensure that there is no gap when a new currency is used
		for currency in self.x.currencyList():

			# Arbitrage opportunities
			self.opportunityList[currency] = []

			# Calculate the gain with each triangular trqansactions
			for order in self.orderBook[currency]:

				# Get the timestamp
				timestamp = order['order'].getPair().getTimestamp()
				# Update the rate of this order chain
				order['order'].updateChain()
				# Estimate the final currency amount of this order
				amount = order['order'].estimateChain(initialAmount)
				# Calculate the gain and save the opportunity if gain is sufficient
				gainPercent = (amount - initialAmount) * 100
				# Identify the first order rate
				rate = order['order'].getRate()

				# Before it can check if this is an opportunity, make sure the data are valid
				if order.has_key('timestamp') and (timestamp - order['timestamp']) <= self.MAX_TIMESTAMP_SPREAD:

					# Check if there is an opportunity here
					if gainPercent > self.GAIN_THRESHOLD_PERCENT:

						# If so identify the weak pair
						# Calculate if the first order is the weak pair
						diffRate = ((rate - order['rate']) / order['rate']) * 100
						# Calculate if the first order is the weak pair
						diffGain = ((amount - order['amount']) / order['amount']) * 100

						# Determine if this is the weak pair, if it affects the arbitrage of this pair
						if diffGain > 0.01 and diffRate > 0.01 and abs(diffGain - diffRate) < 0.1:
							order['weakPair'] = True
						# Still a weak pair if the rate and gain have not changed adjusted
						elif order['weakPair'] == True and diffRate >= 0. and diffGain >= 0.:
							order['weakPair'] = True
						else:
							order['weakPair'] = False

						# Save this opportunity if and only if it starts with a weak pair
						if order['weakPair'] == True:
							# Print the opportunity
							UtilzLog.opportunity("(%+.2f%%) - %s" % (gainPercent, order['order'].printEstimate()))
							# Store it
							self.opportunityList[currency].append(order)

				# By default the first order becames a weak pair
				else:
					order['weakPair'] = False

				# Save the timestamp
				order['timestamp'] = timestamp
				# Save the amount
				order['amount'] = amount
				# Save the gain
				order['gain'] = gainPercent
				# Save the first order rate
				order['rate'] = rate

			# Sort the opportunities to get the most profitable first
			self.opportunityList[currency] = sorted(self.opportunityList[currency], key=lambda o: -o['gain'])

	def process(self, currency, amount = 1.):
		"""
		Process the algorithm
		"""
		# Look if there are potential opportunities
		for order in self.opportunityList[currency]:
			# Get the first order, it must be the most profitable one
			order = order['order']
			order2 = order.cloneInverse()
			# Calculates the minimal rate
			order.getPair()
			finalAmount = order.estimate(amount)
			rate = (amount + order2.getTransaction().getFee(finalAmount)) / finalAmount
			# Update the order and set the conditions
			order2.setRate(rate)
			order2.setConditions(rate, "minRate")
			order2.setConditions(10000000, "timeout")
			# Add this order to the queue
			order.chain.append(order2)
			# Execute the first order
			return order
		return None

	def createChainOrders(self, transactions):
		"""
		Transform the transactions into orders
		"""
		# Initialize the order book
		self.orderBook = {}
		# Loop throguht the currencies
		for currency in self.transactions:
			# Create a new entry
			self.orderBook[currency] = []
			# Calculate the gain with each triangular transactions
			for transactionList in self.transactions[currency]:
				# Loop through the transactions
				currency1 = currency
				# Creates an empty order
				order = None
				for currency2 in transactionList:
					# Create a buy order from this pair
					o = self.x.getPair(currency1, currency2).orderSell()
					# Add conditions to this order
					o.setConditions(self.ORDER_TIMEOUT, "timeout")
					# Add this order
					if order == None:
						order = o
					else:
						order.addChainOrder(o)
					# Shift currency
					currency1 = currency2
				# Save this new order chain
				if order != None:
					self.orderBook[currency].append({'order': order})

	def identifyTransactions(self, currency):
		"""
		This function identify from a currency the possible triangular transactions
		"""
		# Recursive function to identify the possible transactions
		def identifyTransactionsRec(initialCurrency, currency, ignoreCurrencies = [], transactionNum = 1):
			# If the maximal transaction number is reached
			if transactionNum > self.MAX_DEPTH:
				return []
			# Read the pairs from the actual currency
			pairs = self.x.getPair(currency)
			transactions = []
			for currency2 in pairs:
				if currency2 in ignoreCurrencies:
					continue
				# If the transaction number is within the window and it matches the initial currency
				if transactionNum >= self.MIN_DEPTH and currency2 == initialCurrency:
					transactions.append([currency2])
				else:
					result = identifyTransactionsRec(initialCurrency, currency2, ignoreCurrencies + [currency2], transactionNum + 1)
					for c in result:
						transactions.append([currency2] + c)
			if len(transactions) == 0:
				return []
			return transactions

		# Initiate the recursive function
		return identifyTransactionsRec(currency, currency)

