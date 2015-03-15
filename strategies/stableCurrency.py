#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.exchange import *
from exchanges.order import *
from exchanges.orderUtilz import *
from exchanges.currency import *
from utilz.object import *
from utilz.log import *

class stableCurrency(object):
	"""
	This algorithm implements a back to stable currency strategy.
	If there a positive balance in a non-stable currency, and no order pending,
	it will try to bring back all the balance to this stable currency.
	"""

	GAIN_THRESHOLD_PERCENT = 0.5

	STABLE_CURRENCY_LIST = Currency.stable()

	def __init__(self, exchange):
		# Save the exchange for future use
		self.x = exchange
		# Establish the exchange path to the stable currencies
		self.currencyRates = {}
		self.initalValues = {}
		for currency in self.STABLE_CURRENCY_LIST:
			self.currencyRates[currency] = OrderUtilz.identifyCurrencyRates(exchange, currency)
			UtilzLog.info("Currency rates for currency `%s':" % (currency))
			for c in self.currencyRates[currency]:
				# Ignore if None
				if self.currencyRates[currency][c] == None:
					continue
				# Update the rates of the orders
				self.currencyRates[currency][c].updateChain()
				# Display the chain
				UtilzLog.info("From `%s': %s" % (c, str(self.currencyRates[currency][c])), 3)
			# Identify the initial balance of the exchange rate in the various stable currencies
			self.initalValues[currency] = OrderUtilz.estimateValue(exchange.getTotalBalance(), self.currencyRates[currency])
			# Display the portfolio value
			UtilzLog.info("Total estimated value %f %s" % (self.initalValues[currency], currency))

	def preprocess(self):
		"""
		Pre-process the algorithm
		"""
		# Check if there are orders pending
		pass

	def process(self, currency, amount = 1.):
		"""
		Process the algorithm
		"""
		# If this currency is on the volatile currency list
		if currency in self.STABLE_CURRENCY_LIST:
			# Calculate the value of the balance
			#self.initalValues[currency] = OrderUtilz.estimateValue(exchange.getTotalBalance(), self.currencyRates[currency])
			pass