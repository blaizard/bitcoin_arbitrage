#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from utilz.log import *
from utilz.object import *

class Transaction(object):
	"""
	This class offer a way to manage transactions

	A transaction is an convertion from an amount of currency1 to a value of currency2
	"""
	# By default simulation is on
	simulation = True

	def __init__(self, config = {}):
		defaults = {
			# List of fee ordered from the maximum minAmount to the minimum
			'fees': [{
				# Fixed fee applied to the transaction
				'fixed': 0,
				# Percentage of the amount to apply for the transaction
				'percentage': 0,
				# Minimal amount needed for this fee
				'minAmount': 0
			}],
			'limits': {
				# Minimum rate allowed the transaction
				'minRate': 0,
				# Maximum rate allowed the transaction
				'maxRate': 0,
				# Minimum amount of item that can be used for the transaction
				'minAmount': 0,
				# Maximum amount of item that can be used for the transaction
				'maxAmount': 0,
				# Minimum value of the transaction
				'minValue': 0,
				# Maximum value of the transaction
				'maxValue': 0,
				# Maximum number of decimal to be used for the transaction
				'maxDecimal': 0
			},
			'time': {
				# Time in seconds for the transaction to be effective
				'effective': 0,
				# Time in seconds for the transaction to be completed
				'completed': 0
			}
		}
		# Set the default values
		self.config = defaults.copy()
		# Update the limits
		if config.has_key("limits"):
			self.config["limits"].update(config["limits"])
		# Update the time
		if config.has_key("time"):
			self.config["time"].update(config["time"])
		# Update the fees
		if config.has_key("fees"):
			fees = config["fees"]
			# Make sure this is a list, if not create one
			if not isinstance(fees, list):
				fees = [fees]
			# Loop through each elements
			for i, fee in enumerate(fees):
				fees[i] = defaults["fees"][0].copy()
				fees[i].update(fee)
			# Sort and store the fees
			self.config["fees"] = sorted(fees, key=lambda x: -x['minAmount'])

	def clone(self):
		"""
		Returns a clone transaction of this one
		"""
		return Transaction(self.config.copy())

	def inverse(self):
		"""
		Inverse a transaction
		It basically inverse the min and max rate of the transaction
		"""
		minRate = 0
		maxRate = 0
		if self.config['limits'].has_key('minRate') and self.config['limits']['minRate'] != 0:
			maxRate = 1. / self.config['limits']['minRate']
		if self.config['limits'].has_key('maxRate') and self.config['limits']['maxRate'] != 0:
			minRate = 1. / self.config['limits']['maxRate']
		self.config['limits']['minRate'] = minRate
		self.config['limits']['maxRate'] = maxRate
		# Amount becomes value and value amount
		minAmount = 0
		maxAmount = 0
		minValue = 0
		maxValue = 0
		if self.config['limits'].has_key('minAmount'):
			minValue = self.config['limits']['minAmount']
		if self.config['limits'].has_key('maxAmount'):
			maxValue = self.config['limits']['maxAmount']
		if self.config['limits'].has_key('minValue'):
			minAmount = self.config['limits']['minValue']
		if self.config['limits'].has_key('maxValue'):
			maxAmount = self.config['limits']['maxValue']
		self.config['limits']['minAmount'] = minAmount
		self.config['limits']['maxAmount'] = maxAmount
		self.config['limits']['minValue'] = minValue
		self.config['limits']['maxValue'] = maxValue
		# For chainability
		return self

	def __str__(self):
		string_items = []
		# Fees
		string_fees = []
		for i, fee in enumerate(self.config['fees']):
			string_fee = ""
			if fee.has_key('fixed') and fee['fixed'] != 0:
				string_fee = str(fee['fixed'])
			if fee.has_key('percentage') and fee['percentage'] != 0:
				string_fee = string_fee + ("%s%s%%" % ("+" if string_fee else "", str(fee['percentage'])))
			if fee.has_key('minAmount') and fee['minAmount'] != 0:
				string_fee = string_fee + " @ " + str(fee['minAmount'])
			if string_fee == "":
				string_fee = "0"
			string_fees.append(string_fee)
		if len(string_fees) > 0:
			string_items.append("fee:" + ",".join(string_fees))
		# Limits
		limits = self.config['limits']
		for key in limits:
			if limits.has_key(key) and limits[key] != 0:
				string_items.append("%s:%s" % (str(key), str(limits[key])))
		# Time
		if self.config.has_key('time'):
			for key in self.config['time']:
				if self.config['time'][key] != 0:
					string_items.append("time_%s:%f" % (str(key), self.config['time'][key]))
		# Build the string
		return "; ".join(string_items)

	def getMaxDecimal(self):
		"""
		Returns the maximum number of decimal for the transaction
		By default use up to 9 decimals
		"""
		if self.config.has_key('limits') and self.config['limits'].has_key('maxDecimal') and self.config['limits']['maxDecimal'] != 0:
			return self.config['limits']['maxDecimal']
		return 9

	def getTimeEffective(self):
		"""
		Return the effective time of the transaction, when it takes place
		"""
		if self.config.has_key('time') and self.config['time'].has_key('effective'):
			return self.config['time']['effective']
		return 0

	def getTimeCompleted(self):
		"""
		Return the completion time of the transaction, once the money is reflected on the account
		"""
		if self.config.has_key('time') and self.config['time'].has_key('completed'):
			return self.config['time']['completed']
		return 0

	def withinLimits(self, rate, amount):
		"""
		Return True if the order is within the limits, False otherwise
		"""
		if self.config['limits'].has_key('minRate') and self.config['limits']['minRate'] != 0:
			if rate < self.config['limits']['minRate']:
				return [False, "Rate `%f' is below the limit (`%f') allowed by the transaction" % (rate, self.config['limits']['minRate'])]
		if self.config['limits'].has_key('maxRate') and self.config['limits']['maxRate'] != 0:
			if rate > self.config['limits']['maxRate']:
				return [False, "Rate `%f' is above the limit (`%f') allowed by the transaction" % (rate, self.config['limits']['maxRate'])]
		if self.config['limits'].has_key('minAmount') and self.config['limits']['minAmount'] != 0:
			if amount < self.config['limits']['minAmount']:
				return [False, "Amount `%f' is below the limit (`%f') allowed by the transaction" % (amount, self.config['limits']['minAmount'])]
		if self.config['limits'].has_key('maxAmount') and self.config['limits']['maxAmount'] != 0:
			if amount > self.config['limits']['maxAmount']:
				return [False, "Amount `%f' is above the limit (`%f') allowed by the transaction" % (amount, self.config['limits']['maxAmount'])]
		if self.config['limits'].has_key('minValue') and self.config['limits']['minValue'] != 0:
			if amount * rate < self.config['limits']['minValue']:
				return [False, "Value `%f' of the transaction is below the limit (`%f')" % (amount * rate, self.config['limits']['minValue'])]
		if self.config['limits'].has_key('maxValue') and self.config['limits']['maxValue'] != 0:
			if amount * rate > self.config['limits']['maxValue']:
				return [False, "Amount `%f' is above the limit (`%f') allowed by the transaction" % (amount * rate, self.config['limits']['maxValue'])]
		return [True]

	def getFee(self, amount):
		"""
		This function will calculate the fee based on the amount
		Returns -1 in case of error
		"""
		# Look for the fee for this amount
		for fee in self.config['fees']:
			if amount >= fee['minAmount']:
				return fee['fixed'] + amount * fee['percentage'] / 100.
		# No fee has been found, raise an error
		raise error("No fee has been found for this amount.")
