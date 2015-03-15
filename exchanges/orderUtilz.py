#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.exchange import *
from exchanges.order import *
from utilz.object import *
from utilz.log import *

class OrderUtilz(object):

	@staticmethod
	def identifyCurrencyRates(exchange, currency):
		"""
		Identify all the rates of the currencies of this exchange market from a base currency
		\param exchange The exchange market from where this applies
		\param currency The base currency
		\return a table containing all currencies order chains to pass from a currency to the stable one
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
		orderRates = {}
		for c in exchange.currencyList():
			orderRates[c] = identify(exchange, c, currency)

		return orderRates

	@staticmethod
	def estimateValue(balance, currencyRates):
		"""
		Estimates the total value of the balance of an exchange market.
		\param balance The balance of to convert
		\param currencyRates The rates of the currency to the desired currency
		\return The estimated value of the balance
		"""
		# Total value
		value = 0.
		for currency in balance:
			# Continue only if there is money in the balance
			if balance[currency] <= 0:
				continue
			if not currencyRates.has_key(currency):
				raise error("The conversion rate to `%s' is missing" % (str(currency)))
			order = currencyRates[currency]
			if order != None:
				# Update the rates and estimate the value
				value = value + order.updateChain().estimateChain(balance[currency])
			else:
				value = value + balance[currency]
		return value
