#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

class Currency(object):
	BTC = "BTC"
	USD = "USD"
	EUR = "EUR"
	RUR = "RUR"
	CNH = "CNH"
	GBP = "GBP"
	LTC = "LTC"
	NMC = "NMC"
	NVC = "NVC"
	TRC = "TRC"
	PPC = "PPC"
	FTC = "FTC"
	XPM = "XPM"

	@staticmethod
	def volatile():
		"""
		Return the list of volatile currencies
		"""
		return [Currency.BTC, Currency.LTC]


	@staticmethod
	def stable():
		"""
		Return the list of stable currencies
		"""
		return [Currency.USD, Currency.EUR, Currency.GBP, Currency.RUR, Currency.CNH]
