#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.exchange import *
from exchanges.order import *
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

	def __init__(self, exchange):
		# Save the exchange for future use
		self.x = exchange

	def preprocess(self):
		"""
		Pre-process the algorithm
		"""
		# Check if there are orders pending
		pass

	def process(self, currency):
		"""
		Process the algorithm
		"""
		# If this currency is on the volatile currency list
		if currency in Currency.volatile():
			pass
