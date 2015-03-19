#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.exchange import *
from exchanges.order import *
from exchanges.orderUtilz import *
from exchanges.currency import *
from utilz.object import *
from utilz.log import *

import time

class stableCurrency(object):
	"""
	This algorithm implements a back to stable currency strategy.
	If there a positive balance in a non-stable currency, and no order pending,
	it will try to bring back all the balance to this stable currency.
	"""

	GAIN_THRESHOLD_PERCENT = 0.5

	STABLE_CURRENCY_LIST = [Currency.USD]

	STABLE_STATE_TIMER_S = 10

	def __init__(self, exchange):
		# Save the exchange for future use
		self.x = exchange
		# Set the state of the algorithm
		self.state = "idle"
		self.timer = 0
		# Establish the exchange path to the stable currencies
		self.currencyRates = {}
		for currency in self.STABLE_CURRENCY_LIST:
			self.currencyRates[currency] = OrderUtilz.identifyCurrencyRates(exchange, currency)
		# Update the initial balances
		self.updateInitialBalance()

	def updateInitialBalance(self):
		self.initalValues = {}
		# Get the total balance
		balance = self.x.getTotalBalance()
		# Loop through the stable currencies
		for currency in self.STABLE_CURRENCY_LIST:
			for c in self.currencyRates[currency]:
				# Ignore if None
				if not self.currencyRates[currency].has_key(c) or self.currencyRates[currency][c] == None:
					continue
				# Update the rates of the orders
				self.currencyRates[currency][c].updateChain()
			# Identify the initial balance of the exchange rate in the various stable currencies
			self.initalValues[currency] = OrderUtilz.estimateValue(balance, self.currencyRates[currency])
			# Display the portfolio value
			UtilzLog.info("Total estimated balance in `%s': %f" % (currency, self.initalValues[currency]))

	def process(self, amountList):
		"""
		Process the algorithm
		"""

		if self.state == "idle":

			# Get the total balance
			balance = self.x.getTotalBalance()
			availableBalance = self.x.getBalance()

			# If this currency is on the volatile currency list
			for currency in self.STABLE_CURRENCY_LIST:
				# Only update the currencies available
				for c in balance:
					# Ignore if None
					if not self.currencyRates[currency].has_key(c) or self.currencyRates[currency][c] == None:
						continue
					# Update the rates of the orders
					self.currencyRates[currency][c].updateChain()
				# Identify the total value of the balance in the different currencies
				currentValue = OrderUtilz.estimateValue(balance, self.currencyRates[currency])
				# Calculate the gain
				gainPercent = ((currentValue - self.initalValues[currency]) / self.initalValues[currency]) * 100
				#print "%s %f%% [%f vs %f]" % (currency, gainPercent, currentValue, self.initalValues[currency])
				# Compare with the initial value and if it passes the threshold, sell!
				if gainPercent >= self.GAIN_THRESHOLD_PERCENT:
					# Sell everything
					orderList = []
					for c in availableBalance:
						# Ignore if None
						if not self.currencyRates[currency].has_key(c) or self.currencyRates[currency][c] == None:
							continue
						# Clone the order
						order = self.currencyRates[currency][c].clone()
						# Set the amount
						order.setAmount(availableBalance[c])
						# Add the order to the list
						orderList.append(order)
					# Change the state
					self.state = "order"
					return orderList
			return None

		elif self.state == "order":

			self.timer = time.time()
			self.state = "selling"

		elif self.state == "selling":

			if time.time() - self.timer < self.STABLE_STATE_TIMER_S:
				return None

			# Check the status of the orders, make sure none are pending
			if len(Order.getPlacedList()) == 0:
				self.state = "idle"
				# Update the initial balances
				self.updateInitialBalance()
			return None
		return None