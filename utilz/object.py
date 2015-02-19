#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

import copy
import pprint

class UtilzObject(object):
	"""
	Utility functions for objects
	"""
	@staticmethod
	def p(x):
		"""
		Print the attribute of the object
		"""
		pp = pprint.PrettyPrinter(indent=4)
		pp.pprint(x)

	@staticmethod
	def clone(x):
		"""
		Create a clone of x
		"""
		return copy.deepcopy(x)