#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.port.btce import *
from exchanges.currency import *
from exchanges.transaction import *
from exchanges.orderUtilz import *
from utilz.data import UtilzData
from utilz.log import *
from utilz.object import *
from strategies.triangularArbitrage import *
from strategies.stableCurrency import *
from bot import *
from privateConfig import *

import time

class ExchangeValidation(Exchange):
	"""
	This is a dummy exchange place used for validation purpose
	"""

	def initialize(self):
		# Setup name of the exchange
		self.context["name"] = "Validation"
		# Set a dummy pair
		self.pairAdd(ExchangePair({
			'baseCurrency': Currency.EUR,
			'quoteCurrency': Currency.USD,
			'sell': Transaction({'fees': [{'percentage': 0}]}),
			'buy': Transaction({'fees': [{'percentage': 0}]})
		}))

	def updatePairs(self):
		"""
		Update the pair rates
		"""
		self.pairUpdate(Currency.EUR, Currency.USD, {
			'ask': 1.4746,
			'bid': 1.4745
		})

def validation():
	# Create and update the exchange
	ex = ExchangeValidation()
	ex.updatePairs()
	print ex
	# Get the pairs
	eur_usd = ex.getPair(Currency.EUR, Currency.USD)
	usd_eur = ex.getPair(Currency.USD, Currency.EUR)
	# Place dummy orders
	buy_eur_usd = eur_usd.orderBuy()
	buy_eur_usd.update()
	sell_eur_usd = eur_usd.orderSell()
	sell_eur_usd.update()
	buy_usd_eur = usd_eur.orderBuy()
	buy_usd_eur.update()
	sell_usd_eur = usd_eur.orderSell()
	sell_usd_eur.update()

	print "BUY  (1 USD) -> %s -> %s" % (buy_eur_usd, buy_eur_usd.estimate(1.))
	print "SELL (1 EUR) -> %s -> %s" % (sell_eur_usd, sell_eur_usd.estimate(1.))
	print "BUY  (1 EUR) -> %s -> %s" % (buy_usd_eur, buy_usd_eur.estimate(1.))
	print "SELL (1 USD) -> %s -> %s" % (sell_usd_eur, sell_usd_eur.estimate(1.))

def testExchange(exchange):
	"""
	This function will test an exchange by doing some transactions
	"""
	# Set the Nonce
	exchange.btceAPI("getInfo")

	# Update the rates
	exchange.updatePairs()

	# Look at the active order list
	exchange.updateOrdersPort()
	# Get the pairs
	eur_usd = exchange.getPair(Currency.EUR, Currency.USD)
	# Create the order
	order = eur_usd.orderBuy()
	order.update()
	order.setAmount(1.)

	# Trade a small amount
	exchange.tradePort(order)
	while True:
		# Look at the active order list
		exchange.updateOrdersPort()

if __name__ == "__main__":

	# Set the proxy if needed
	#UtilzData.setProxy({'http': 'http://squid.norway.atmel.com:3128', 'https': 'http://squid.norway.atmel.com:3128'})
	# Set the verbosity level
	UtilzLog.setVerbosity(3)

	# Disble simulation mode
	# !! Warning !! This will deal with the real money
#	Exchange.disableSimulationMode()

	# Validation function
#	validation()
#	exit()

	#config = {'recordWrite': ("records/%s-%s-btce.txt" % (time.strftime("%Y.%m.%d"), time.strftime("%H.%M.%S")))}
	#config = {'recordRead': "../bitcoin_arbitrage_records/2015.01.22-14.16.48-btce-+0.08%.txt"}
	config = {}
	config['apiKey'] = BTCE_APIKEY
	config['apiSecret'] = BTCE_APISECRET

	btce = ExchangeBTCE(config)

	b = Bot({
		'exchanges': [btce],
		'algorithms': [triangularArbitrage, stableCurrency],
		'debug': True
	})
	b.run()

