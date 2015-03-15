#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.exchange import *
from exchanges.currency import *
from exchanges.transaction import *
from exchanges.order import *
from utilz.log import *
from utilz.data import *

import hashlib
import hmac
import urllib
import re
import threading

class ExchangeBTCE(Exchange):
	"""
	Support of the BTC-E bitcoin exchange
	"""

	SUPPORTED_PAIRS = {
		"btc_usd": [Currency.BTC, Currency.USD],
		"btc_rur": [Currency.BTC, Currency.RUR],
		"btc_eur": [Currency.BTC, Currency.EUR],
		"btc_cnh": [Currency.BTC, Currency.CNH],
		"btc_gbp": [Currency.BTC, Currency.GBP],
		"ltc_btc": [Currency.LTC, Currency.BTC],
		"ltc_usd": [Currency.LTC, Currency.USD],
		"ltc_rur": [Currency.LTC, Currency.RUR],
		"ltc_eur": [Currency.LTC, Currency.EUR],
		"ltc_cnh": [Currency.LTC, Currency.CNH],
		"ltc_gbp": [Currency.LTC, Currency.GBP],
		"nmc_btc": [Currency.NMC, Currency.BTC],
		"nmc_usd": [Currency.NMC, Currency.USD],
		"nvc_btc": [Currency.NVC, Currency.BTC],
		"nvc_usd": [Currency.NVC, Currency.USD],
		"usd_rur": [Currency.USD, Currency.RUR],
		"eur_usd": [Currency.EUR, Currency.USD],
		"eur_rur": [Currency.EUR, Currency.RUR],
		"usd_cnh": [Currency.USD, Currency.CNH],
		"gbp_usd": [Currency.GBP, Currency.USD],
		#"trc_btc": [Currency.TRC, Currency.BTC],
		"ppc_btc": [Currency.PPC, Currency.BTC],
		"ppc_usd": [Currency.PPC, Currency.USD],
		#"ftc_btc": [Currency.FTC, Currency.BTC],
		#"xpm_btc": [Currency.XPM, Currency.BTC]
	}

	nonce = 1

	def initialize(self):
		# Set the name of the exchange
		self.context["name"] = "BTC-e"
		# Fetch info from the exchange
		info = UtilzData().fetch({'url': "https://btc-e.com/api/3/info"}).fromJSON().get()
		# Make sure there is no error
		if not info.has_key("pairs"):
			raise error("The response is malformed `%s'." % (str(data)))
		# Loop through the pairs
		for key in self.SUPPORTED_PAIRS:
			currency_pair = self.SUPPORTED_PAIRS[key]
			if not info["pairs"].has_key(key):
				raise error("This pair is not supported `%s'." % (str(key)))
			# Identify the info needed
			infoKey = info["pairs"][key]
			# Build the exchange information
			defaults_limits = {
				'minRate': infoKey["min_price"],
				'maxRate': infoKey["max_price"],
				'minAmount': infoKey["min_amount"],
				'maxDecimal': infoKey["decimal_places"]
			}
			# Setup the exchange
			self.pairAdd(ExchangePair({
					'baseCurrency': currency_pair[0],
					'quoteCurrency': currency_pair[1],
					'sell': Transaction({
						#'fees': [{'percentage': 0}], # For testing purpose
						'fees': [{'percentage': infoKey["fee"]}],
						'limits': {
							'minRate': infoKey["min_price"],
							'maxRate': infoKey["max_price"],
							'minAmount': infoKey["min_amount"],
							'maxDecimal': infoKey["decimal_places"]
						},
						'time': {
							'effective': 1, # Emulates the time it takes from the transaction to go through
							'completed': 2
						}}),
					'buy': Transaction({
						#'fees': [{'percentage': 0}], # For testing purpose
						'fees': [{'percentage': infoKey["fee"]}],
						'limits': {
							'minRate': 1. / infoKey["max_price"],
							'maxRate': 1. / infoKey["min_price"],
							'minValue': infoKey["min_amount"], # Amount becomes value when buy
							'maxDecimal': infoKey["decimal_places"]
						},
						'time': {
							'effective': 1, # Emulates the time it takes from the transaction to go through
							'completed': 2
						}}),
					'withdraw': Transaction({'time': { 'completed': 2 * 3600 * 24 }})
				}, key)
			)
		# Initialize the account if simulation is False only
		if self.simulation == False:
			# Set the semaphore for accessing the API
			self.semaphore = threading.Semaphore()
			# Update the nonce number if needed
			self.syncNonce()
			self.updateBalancePort()

	def syncNonce(self):
		self.btceAPI("getInfo", retry = False)

	def updateBalancePort(self, info = None):
		"""
		Updates the balance
		"""
		if info == None:
			info = self.btceAPI("getInfo")
			if info[0] == False:
				raise error("`%s' error: %s" % (self.getName(), info[1]))
			info = info[1]
		balance = {}
		if not info.has_key("funds") or not isinstance(info['funds'], dict):
			raise error("Invalid getInfo response.")
		if info["funds"].has_key("btc"):
			balance[Currency.BTC] = info["funds"]["btc"]
		if info["funds"].has_key("ltc"):
			balance[Currency.LTC] = info["funds"]["ltc"]
		if info["funds"].has_key("nmc"):
			balance[Currency.NMC] = info["funds"]["nmc"]
		if info["funds"].has_key("nvc"):
			balance[Currency.NVC] = info["funds"]["nvc"]
		if info["funds"].has_key("usd"):
			balance[Currency.USD] = info["funds"]["usd"]
		if info["funds"].has_key("eur"):
			balance[Currency.EUR] = info["funds"]["eur"]
		if info["funds"].has_key("gbp"):
			balance[Currency.GBP] = info["funds"]["gbp"]
		if info["funds"].has_key("trc"):
			balance[Currency.TRC] = info["funds"]["trc"]
		if info["funds"].has_key("ppc"):
			balance[Currency.PPC] = info["funds"]["ppc"]
		if info["funds"].has_key("ftc"):
			balance[Currency.FTC] = info["funds"]["ftc"]
		if info["funds"].has_key("rur"):
			balance[Currency.RUR] = info["funds"]["rur"]
		if info["funds"].has_key("cnh"):
			balance[Currency.CNH] = info["funds"]["cnh"]
		if info["funds"].has_key("xpm"):
			balance[Currency.XPM] = info["funds"]["xpm"]
		# Update the balance
		self.setBalance(balance)

	def btceAPI(self, method, args = {}, retry = True):
		"""
		Generic function to get info from the private API
		"""
		# Acquire the sempahore
		self.semaphore.acquire()

		params = {
			"method": method,
			"nonce": self.nonce
		}
		# Add the parameters if any
		params.update(args)
		# Update the nonce request
		self.nonce = self.nonce + 1
		# Update the params
		params = urllib.urlencode(params)
		# Hash the params string to produce the Sign header value
		h = hmac.new(self.config['apiSecret'], digestmod = hashlib.sha512)
		h.update(params)
		sign = h.hexdigest()
		# Generate the headers
		headers = {
			"Key": self.config['apiKey'],
			"Sign": sign
		}
		# Fetch the result
		try:
			result = UtilzData().fetch({
				'url': "https://btc-e.com/tapi",
				'post': params,
				'headers': headers
			}).fromJSON().get()
		except:
			# Release the sempahore
			self.semaphore.release()
			return [False, "Error while fetching `https://btc-e.com/tapi'"]

		# Release the sempahore
		self.semaphore.release()

		# If there is an error
		isError = False
		if not result.has_key("success") or result["success"] != 1:
			isError = True
			if result.has_key("error"):
				message = str(result['error'])
			else:
				message = str(result['result'])
		elif not result.has_key("return") or not isinstance(result['return'], dict):
			isError = True
			message = str(result)

		# Handle error
		if isError == True:

			# Check if the nonce number is not in sync
			m = re.match(".*you should send:([0-9]+).*", message)
			if m:
				self.nonce = int(m.group(1))
				if retry:
					UtilzLog.info("`%s' Adjusting nonce to `%i' and retrying command `%s'" % (self.getName(), self.nonce, method), 1)
					# Retry with the new nonce
					return self.btceAPI(method, args)
				else:
					UtilzLog.info("`%s' Adjusting nonce to `%i'" % (self.getName(), self.nonce), 1)

			return [False, message]

		# Return the result only if successfull
		return [True, result['return']]

	def tradePort(self, order):
		"""
		Make a trade
		"""
		info = order.getInfo()
		# Identify the pair
		pair = None
		for key in self.SUPPORTED_PAIRS:
			c = self.SUPPORTED_PAIRS[key]
			if c[0] == info['pair'].getBaseCurrency() and c[1] == info['pair'].getQuoteCurrency():
				pair = key
				break
		# If the pair has not been identified
		if pair == None:
			return [False, "Unable to identify the pair for this order `%s'" % (str(info['pair']))]

		# Identify the rate of the transaction
		if info['type'] == "sell":
			rate = info['rate']
			amount = info['amount']
		elif info['type'] == "buy":
			rate = order.floor(1. / info['rate'])
			amount = order.estimate(mode = Order.ESTIMATE_NO_FEE)
		else:
			return [False, "Unsupported transaction type `%s'" % (info['type'])]

		# Processing order
		UtilzLog.order("`%s' Trading `%s' `%s' rate:%f amount:%f" % (self.getName(), pair, info['type'], rate, amount))

		info = self.btceAPI("Trade", {
			'pair': pair,
			'type': info['type'],
			'rate': rate,
			'amount': amount
		})

		# If there is an error
		if info[0] == False:
			return info

		# Else update the balance
		info = info[1]
		self.updateBalancePort(info)

		return [True, info['order_id']]

	def updateOrdersPort(self):
		"""
		Update the order status
		"""
		info = self.btceAPI("ActiveOrders")

		# Make sure it succeeded
		if info[0] == False:
			if re.match('no orders', info[1]):
				# No orders pending, set them all as completed
				return [True, {}]
			else:
				return info

		activeOrders = info[1]

		orderList = {}
		for identifier in activeOrders:
			# Check the status
			status = Order.STATUS_PENDING
			if activeOrders[identifier]["status"] == 1:
				status = Order.STATUS_COMPLETED
			orderList[identifier] = {
				'status': status,
				'type': activeOrders[identifier]["type"],
				'pair': self.SUPPORTED_PAIRS[activeOrders[identifier]["pair"]],
				'amount': activeOrders[identifier]["amount"],
				'rate': activeOrders[identifier]["rate"]
			}

		return [True, orderList]


	def updatePairsPort(self):
		"""
		This function updates the exchange pairs
		"""
		keys = [key for key in self.SUPPORTED_PAIRS]
		# Fetch info from the exchange
		info = UtilzData().fetch({'url': "https://btc-e.com/api/3/ticker/" + "-".join(keys)}).fromJSON().get()

		# Loop through the pairs and update the values
		for key in self.SUPPORTED_PAIRS:
			currencyPair = self.SUPPORTED_PAIRS[key]
			# Make sure the info exists
			if not info.has_key(key):
				raise error("The info for the the key `%s' is missing." % (str(key)))
			# Read the info for this specific pair
			infoKey = info[key]
			self.pairUpdate(currencyPair[0], currencyPair[1], {
				'high': infoKey["high"],
				'low': infoKey["low"],
				'avg': infoKey["avg"],
				'volume': infoKey["vol"],
				'volumeCurrency': infoKey["vol_cur"],
				'last': infoKey["last"],
				'ask': infoKey["buy"],
				'bid': infoKey["sell"],
				'timestamp': infoKey["updated"]
			})
		# Update the timestamp of the exchange
		self.setTimestamp(infoKey["updated"])
