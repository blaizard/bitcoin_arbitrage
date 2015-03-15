#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from utilz.log import *
from exchanges.exchange import *
from exchanges.currency import *

import sys
import time
import threading

class Bot(object):

	# Initial identifier
	ID = 0
	# Default structure containing the different timings
	time = []
	# Defautl timestamp
	initTimestamp = 0

	def __init__(self, config = {}):
		self.config = {
			'simulationData': {
				'balance': {
					Currency.LTC: 100.
				}
			},
			'trade': {
				# The reference currency
				'currency': Currency.USD,
				# Amount to use for a transaction
				'amount': 10.,
				# Any amount below this balance will not be traded
				'minBalance': 2.
			},
			'exchanges': [],
			'algorithms': [],
			# Debug flag, by default is true
			'debug': True
		}
		self.config.update(config)
		# Pimp the logging
		# This message is used to place an order
		UtilzLog.addPreset("opportunity", {
			'loggingType': "info",
			'colorWrap': "\33[0;32m%s\33[m",
			'defaultLevel': 1
		})
		UtilzLog.addPreset("order", {
			'loggingType': "info",
			'colorWrap': "\33[1;34m%s\33[m",
			'defaultLevel': 1
		})
		UtilzLog.addPreset("display", {
			'loggingType': "info",
			'colorWrap': "%s",
			'defaultLevel': 1
		})
		# Set the Bot ID
		Bot.ID = Bot.ID + 1
		self.identifier = Bot.ID
		# Set the timestamp
		self.initTimestamp = time.time()
		# Initialize the bot
		self.initialize()

	def initialize(self):
		"""
		Initializes the bot and the algorithms if needed
		"""
		UtilzLog.info("Set inital balance on the exchange(s)", 1)
		for ex in self.config['exchanges']:
			ex.setBalance(self.config['simulationData']['balance'])

		self.context = []
		for ex in self.config['exchanges']:
			exchange = {
				'exchange': ex,
				'algorithms': []
			}
			for algorithm in self.config['algorithms']:
				UtilzLog.info("Initializing `%s' for `%s'" % (algorithm.__name__, ex.getName()), 1)
				exchange['algorithms'].append(algorithm(ex))
			self.context.append(exchange)

		UtilzLog.info("Convert currency trading amounts", 1)
		currencyList = []
		baseCurrency = self.config['trade']['currency']
		orderAverageRates = {}
		for ex in self.context:
			# Update the rates
			ex['exchange'].updatePairs()
			# Generate the order list to pass from 1 currency to the base currency
			ex['orderBaseCurrency'] = self.identifyRates(ex['exchange'], baseCurrency)
			# Merge with the average rates
			orderAverageRates.update(ex['orderBaseCurrency'])
			# Make the currency list
			currencyList = currencyList + ex['exchange'].currencyList()
		# Set unique currencies
		currencyList = list(set(currencyList))
		self.tradeAmount = {}
		for c in orderAverageRates:
			self.tradeAmount[c] = {
				'amount': self.config['trade']['amount'],
				'minBalance': self.config['trade']['minBalance']
			}
			order = orderAverageRates[c]
			if order != None:
				order.updateChain(Order.UPDATE_FROM_AVERAGE)
				self.tradeAmount[c]['amount'] = order.estimateChain(self.tradeAmount[c]['amount'], Order.ESTIMATE_INVERSE | Order.ESTIMATE_NO_FEE)
				self.tradeAmount[c]['minBalance'] = order.estimateChain(self.tradeAmount[c]['minBalance'], Order.ESTIMATE_INVERSE | Order.ESTIMATE_NO_FEE)
		# Make sure all currencies are included
		for currency in currencyList:
			if not self.tradeAmount.has_key(currency):
				raise error("This currency `%s' is missing from the convertion." % (currency))
		# Make sure the amount is greater than the minimal amount allowed for the transactions
		for ex in self.context:
			for baseCurrency in self.tradeAmount:
				pairList = ex['exchange'].getPair(baseCurrency)
				for quoteCurrency in pairList:
					pair = pairList[quoteCurrency]
					pair.getTransaction('sell').withinLimits(pair.getBid(), self.tradeAmount[baseCurrency]['amount'])

		UtilzLog.info("Update the orders (if any)", 1)
		for ex in self.context:
			ex['exchange'].updateOrders()

		UtilzLog.info("Estimate intial value in each exchanges:", 1)
		stringList = []
		for ex in self.context:
			# Update the balance
			ex['exchange'].updateBalance()
			# Estimates the value
			value = self.estimateValue(ex)
			# Store the initial value of the balance
			ex['initialValue'] = value
			stringList.append("`%s': %f %s" % (ex['exchange'].getName(), value, self.config['trade']['currency']))
		UtilzLog.info(", ".join(stringList), 1)

	def identifyRates(self, exchange, currency):
		"""
		Identify all the rates of the currencies of this exchange market from a base currency
		"""
		def identify(exchange, c, currency, ignoreCurrencies = [], rate = 1.):
			# If the current currency is the same as c
			if currency == c:
				return None
			pairList = exchange.getPair(c)
			# If the pair to the currency exists
			if pairList.has_key(currency):
				return pairList[currency].orderSell()
			# If a direct pair does not exists
			for c2 in pairList:
				# Ignore some currencies
				if c2 in ignoreCurrencies:
					continue
				# Call the recursive function
				result = identify(exchange, c2, currency, ignoreCurrencies + [c], rate)
				if result != None:
					order = pairList[c2].orderSell()
					order.addChainOrder(result)
					return order
			# Nothing has been found
			return None

		# Compute the rates
		rates = {}
		for c in exchange.currencyList():
			rates[c] = identify(exchange, c, currency)
			# Update the rates
			if rates[c]:
				rates[c].update()

		return rates

	def estimateValue(self, exchange = None):
		"""
		Estimates the total value in a particular exchange place.
		If exchange is not set estimates the value in all exchange places.
		"""
		# Build the exchange list
		if exchange == None:
			exchangeList = [ex['exchange'] for ex in self.context]
		else:
			exchangeList = [exchange]
		# Total value
		value = 0.
		for ex in exchangeList:
			# Read the total balance of this exchange
			balance = ex['exchange'].getTotalBalance()
			for currency in balance:
				# Continue only if there is money in the balance
				if balance[currency] <= 0:
					continue
				order = ex['orderBaseCurrency'][currency]
				if order != None:
					# Update the rates and estimate the value
					value = value + order.updateChain().estimateChain(balance[currency])
				else:
					value = value + balance[currency]
		return value

	def printBalance(self):
		"""
		Print the walet balance
		"""
		string = ""
		for ex in self.context:
			value = self.estimateValue(ex)
			# Estimated balance
			stringBalance = "%f %s" % (value, self.config['trade']['currency'])
			# Progress only if the initial balance is greater than 0
			if ex['initialValue'] > 0:
				stringBalance = "%s (%+.2f%%)" % (stringBalance, (value * 1. / ex['initialValue'] - 1.) * 100)
			# Print the Balance
			string = string + "`%s' at t=%i - Total estimated value %s\n%s\n" % (ex['exchange'].getName(), ex['exchange'].getTimestamp(), stringBalance, ex['exchange'].printBalance())
		return string

	def printTimings(self):
		"""
		Print the timings of the different entities monitored
		"""
		string = ""
		for iEx, t in enumerate(self.time):
			ex = self.context[iEx]
			name = ex['exchange'].getName()
			string = string + "`%s' Total execution time: %.1fms (min:%.1fms; max:%.1fms)\n" % (name, t['loop']['current'] * 1000, t['loop']['min'] * 1000, t['loop']['max'] * 1000)
			string = string + "`%s' Pair update execution time: %.1fms (min:%.1fms; max:%.1fms)\n" % (name, t['updatePairs']['current'] * 1000, t['updatePairs']['min'] * 1000, t['updatePairs']['max'] * 1000)
			for i in range(0, len(t['algorithms'])):
				string = string + "`%s' Algorithm `%s' execution time: %.1fms (min:%.1fms; max:%.1fms)\n" % (name, ex['algorithms'][i].__class__.__name__, t['algorithms'][i]['current'] * 1000, t['algorithms'][i]['min'] * 1000, t['algorithms'][i]['max'] * 1000)
		return string

	def printOrders(self):
		"""
		Display the current active orders
		"""
		def cap(s, l):
			return s if len(s) <= l else s[0:l]

		stringList = []
		for order in Order.getActiveList():
			exchange = order.pair.getExchange()
			stringList.append("`%s'\tid:%s\t%s\t\t%s" % (exchange.getName(), str(order.getId()), cap(str(order.getStatus()), 7), order.printOrder()))
		if len(stringList) > 0:
			return "Active Orders:\n%s\n" % ("\n".join(stringList))
		else:
			return "Active Orders: None\n"

	def taskBalance(self):
		"""
		This tasks takes care of the balance and print it
		"""
		while True:

			# Update the exchanges
			try:
				for ex in self.context:
					ex['exchange'].updateBalance()
			except:
				UtilzLog.display("Error while fetching the balance")

			# Guards if the display has an issue due to some concurent data access
			try:
				# Print info about the bot
				m, s = divmod(time.time() - self.initTimestamp, 60)
				h, m = divmod(m, 60)
				string = "Bot Id: %i (%d:%02d:%02d)\n" % (self.identifier, h, m, s)
				# Print the execution time
				string = string + self.printTimings()
				# Print the balance
				string = string + self.printBalance()
				# Print the actie orders
				string = string + self.printOrders()
			except:
				UtilzLog.display("Error while printing the display")

			# Print the displayed info
			UtilzLog.display(string)

			# Sleep time to update the balance only from time to time
			time.sleep(1)

	def run(self):

		# Start the balance thread
		t = threading.Thread(target = self.taskBalance)
		t.daemon = True
		t.start()

		# Initialize the timing reports
		self.time = []

		# Forever loop
		while True:

			#self.printBalance()


			# Update the exchanges
			for iEx, ex in enumerate(self.context):

				# If this is the first time
				if len(self.time) == 0:
					self.time.append({
						'algorithms': [],
						'updatePairs': {
							'min': sys.maxint,
							'max': 0.,
							'current': 0.
						},
						'loop': {
							'min': sys.maxint,
							'max': 0.,
							'current': 0.
						}
					})
				# Variable to generate the algorithm timings
				timeAlgo = []
				timeLoop = time.clock()

				# Default value for the order
				order = None

				# Fetch data from the outer space
				try:
					# If there are pending orders
					if len(Order.getActiveList()) > 0:
						# Update the orders
						ex['exchange'].updateOrders()
					# Update the exchange pairs (rates)
					timePairs = time.clock()
					if ex['exchange'].updatePairs() == False:
						UtilzLog.p("Final balance:", 1)
						# Update the balance and print it one last time
						ex['exchange'].updateBalance()
						self.printBalance()
						exit()
					timePairs = time.clock() - timePairs


					# Pre-process the algorithms if needed
					for algo in ex['algorithms']:
						start = time.clock()
						algo.preprocess()
						timeAlgo.append(time.clock() - start)

					# Run the algorhtms where there is money
					balance = ex['exchange'].getBalance()
					for currency in balance:
						# Ignore is this curreny is not handled in the exchanged (this happens if a pair has stopped)
						if currency not in ex['exchange'].currencyList():
							continue

						# Ignore if there isnot enough balance on this pair
						if balance[currency] < self.tradeAmount[currency]['minBalance']:
							continue
						# Get the amount we want to trade
						totalAmount = balance[currency]
						amount = min(totalAmount, self.tradeAmount[currency]['amount'])
						# If the amount left is bellow the minimal amount, use everything
						if totalAmount <= amount + self.tradeAmount[currency]['minBalance']:
							amount = totalAmount

						# Run the algorithms
						for i, algo in enumerate(ex['algorithms']):
							start = time.clock()
							order = algo.process(currency, amount)
							timeAlgo[i] = timeAlgo[i] + (time.clock() - start)

							# Check if there is an opportunity
							if order != None:
								# Execute the order
								result = order.execute(amount = amount)
								break
						if order != None:
							break

				except Exception as e:
					UtilzLog.error(str(e))
					if self.config['debug'] == True:
						raise
					continue

				# Calculate the loop time
				timeLoop = time.clock() - timeLoop

				# Update the timings
				for i, algo in enumerate(ex['algorithms']):
					if len(self.time[iEx]['algorithms']) > i:
						t = self.time[iEx]['algorithms'][i]
						t['min'] = min(t['min'], timeAlgo[i])
						t['max'] = max(t['max'], timeAlgo[i])
						t['current'] = timeAlgo[i]
						self.time[iEx]['algorithms'][i] = t
					else:
						t = {
							'min': timeAlgo[i],
							'max': timeAlgo[i],
							'current': timeAlgo[i]
						}
						self.time[iEx]['algorithms'].append(t)
				# Update the full loop timings
				self.time[iEx]['loop']['min'] = min(self.time[iEx]['loop']['min'], timeLoop)
				self.time[iEx]['loop']['max'] = max(self.time[iEx]['loop']['max'], timeLoop)
				self.time[iEx]['loop']['current'] = timeLoop
				# Update the full loop timings
				self.time[iEx]['updatePairs']['min'] = min(self.time[iEx]['updatePairs']['min'], timePairs)
				self.time[iEx]['updatePairs']['max'] = max(self.time[iEx]['updatePairs']['max'], timePairs)
				self.time[iEx]['updatePairs']['current'] = timePairs
