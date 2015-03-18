#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from utilz.log import *
from exchanges.exchange import *
from exchanges.currency import *
from exchanges.orderUtilz import *

import sys
import time
import threading

class Bot(object):

	# Initial identifier
	ID = 0
	# Default structure containing the different timings
	time = []
	# Default timestamp
	initTimestamp = 0

	def __init__(self, config = {}):
		self.config = {
			'simulationData': {
				'balance': {
					Currency.LTC: 100.,
					Currency.BTC: 5.
				}
			},
			'trade': {
				# The reference currency
				'currency': Currency.USD,
				# Amount to use for a transaction
				'amount': 30.,
				# Any amount below this balance will not be traded
				'minBalance': 1.
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

		# Initialize the exchanges
		self.context = []
		for ex in self.config['exchanges']:
			exchange = {
				'exchange': ex,
				'algorithms': []
			}
			self.context.append(exchange)

		UtilzLog.info("Convert currency trading amounts", 1)
		currencyList = []
		baseCurrency = self.config['trade']['currency']
		orderAverageRates = {}
		for ex in self.context:
			# Update the rates
			ex['exchange'].updatePairs()
			# Generate the order list to pass from 1 currency to the base currency
			ex['orderBaseCurrency'] = OrderUtilz.identifyCurrencyRates(ex['exchange'], baseCurrency)
			#ex['orderBaseCurrency'] = self.identifyRates(ex['exchange'], baseCurrency)

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
			value = OrderUtilz.estimateValue(ex['exchange'].getTotalBalance(), ex['orderBaseCurrency'])
			# Store the initial value of the balance
			ex['initialValue'] = value
			stringList.append("`%s': %f %s" % (ex['exchange'].getName(), value, self.config['trade']['currency']))
		UtilzLog.info(", ".join(stringList), 1)

		# Initialize the various algorithms
		for exchange in self.context:
			for algorithm in self.config['algorithms']:
				UtilzLog.info("Initializing `%s' for `%s'" % (algorithm.__name__, exchange['exchange'].getName()), 1)
				exchange['algorithms'].append(algorithm(exchange['exchange']))

	def printBalance(self):
		"""
		Print the walet balance
		"""
		string = ""
		for ex in self.context:
			value = OrderUtilz.estimateValue(ex['exchange'].getTotalBalance(), ex['orderBaseCurrency'])
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
					timings = {
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
					}
					for algo in ex['algorithms']:
						timings['algorithms'].append({
							'min': sys.maxint,
							'max': 0.,
							'current': 0.
						})
					self.time.append(timings)

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
					# Check if this is the last update available, this should only happens when
					if ex['exchange'].updatePairs() == False:
						UtilzLog.p("Final balance:", 1)
						# Update the balance and print it one last time
						ex['exchange'].updateBalance()
						self.printBalance()
						exit()
					timePairs = time.clock() - timePairs

					# Build the list of amounts available for trading
					# This depends on the minimal balance and recommanded amount
					balance = ex['exchange'].getBalance()
					amountList = {}
					for currency in balance:
						# Ignore if this curreny is not handled in the exchanged (this happens if a pair has stopped)
						if currency not in ex['exchange'].currencyList():
							continue
						# Ignore if there is not enough balance on this pair
						if balance[currency] < self.tradeAmount[currency]['minBalance']:
							continue
						# Get the amount we want to trade
						totalAmount = balance[currency]
						amount = min(totalAmount, self.tradeAmount[currency]['amount'])
						# If the amount left is bellow the minimal amount, use everything
						if totalAmount <= amount + self.tradeAmount[currency]['minBalance']:
							amount = totalAmount
						amountList[currency] = amount

					# Run the algorithm
					for algo in ex['algorithms']:

						start = time.clock()
						orderList = algo.process(amountList)
						timeAlgo.append(time.clock() - start)

						# Check if there is an opportunity
						if orderList != None:
							# Execute the orders
							for order in orderList:
								result = order.execute()
							break

				except Exception as e:
					UtilzLog.error(str(e))
					if self.config['debug'] == True:
						raise
					continue

				# Calculate the total loop time
				timeLoop = time.clock() - timeLoop

				# Update the timings
				for i, algo in enumerate(ex['algorithms']):
					# Make sure this algorithm has been measured
					if i >= len(timeAlgo):
						break
					t = self.time[iEx]['algorithms'][i]
					t['min'] = min(t['min'], timeAlgo[i])
					t['max'] = max(t['max'], timeAlgo[i])
					t['current'] = timeAlgo[i]
					self.time[iEx]['algorithms'][i] = t

				# Update the full loop timings
				self.time[iEx]['loop']['min'] = min(self.time[iEx]['loop']['min'], timeLoop)
				self.time[iEx]['loop']['max'] = max(self.time[iEx]['loop']['max'], timeLoop)
				self.time[iEx]['loop']['current'] = timeLoop
				# Update the full loop timings
				self.time[iEx]['updatePairs']['min'] = min(self.time[iEx]['updatePairs']['min'], timePairs)
				self.time[iEx]['updatePairs']['max'] = max(self.time[iEx]['updatePairs']['max'], timePairs)
				self.time[iEx]['updatePairs']['current'] = timePairs
