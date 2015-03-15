#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

import logging
import sys

class UtilzLog(object):
	LOG_DEFAULT_LEVEL_ERROR = 0
	LOG_DEFAULT_VERBOSE_LEVEL = 1

	PRESETS = {
		'info': {
			'loggingType': "info",
			'colorWrap': "%s",
			'defaultLevel': 3
		},
		'error': {
			'loggingType': "error",
			'colorWrap': "\33[1;31m%s\33[m",
			'defaultLevel': LOG_DEFAULT_LEVEL_ERROR
		},
		'warning': {
			'loggingType': "warn",
			'colorWrap': "\33[0;31m%s\33[m",
			'defaultLevel': 2
		},
		'workaround': {
			'loggingType': "info",
			'colorWrap': "\33[0;36m%s\33[m",
			'defaultLevel': 3
		},
		'debug': {
			'loggingType': "debug",
			'colorWrap': "\33[0;32m%s\33[m",
			'defaultLevel': 1
		},
		'bench': {
			'loggingType': "debug",
			'colorWrap': "\33[1;35m%s\33[m",
			'defaultLevel': 1
		}
	}

	# Log instance
	log = None

	def __init__(self, level = LOG_DEFAULT_VERBOSE_LEVEL):
		# Set this instance as the main one
		UtilzLog.log = self

		# Create the logger
		logger = logging.getLogger('log')
		logger.setLevel(logging.DEBUG)
		# Set the logging handler
		UtilzLog.setHandler(logging.StreamHandler(stream = sys.stdout))

		UtilzLog.setVerbosity(level)
		# Clean up the hooks
		UtilzLog.hooks = {}

		# Clean up the preset list
		UtilzLog.presets = {}
		# Add the presets
		for name in UtilzLog.PRESETS:
			UtilzLog.addPreset(name, UtilzLog.PRESETS[name])

	@classmethod
	def addPreset(cls, name, preset):
		# Set default values to the preset
		p = {
			'loggingType': "info",
			'preWrap': "%s",
			'colorWrap': "%s",
			'defaultLevel': 3
		}
		p.update(preset)
		f = lambda m, l=p['defaultLevel']: UtilzLog.p(p['preWrap'] % (str(m)), l, name)
		setattr(cls, name, staticmethod(f))
		# Add the preset information
		UtilzLog.presets[name] = p

	@staticmethod
	def setHandler(handler):
		handler.setLevel(logging.DEBUG)
		formatter = logging.Formatter("[%(asctime)-15s] [%(preset)s %(level)s] - %(message)s")
		handler.setFormatter(formatter)
		logger = logging.getLogger('log')
		logger.addHandler(handler)

	@staticmethod
	def setVerbosity(level):
		setattr(UtilzLog, "verboseLevel", int(level))

	@staticmethod
	def setHook(preset, fct, args = None):
		# Store the function pointer
		UtilzLog.hooks[preset] = [fct, args]
		setattr(UtilzLog, "hooks", UtilzLog.hooks)

	@staticmethod
	def setFile(filename):
		logger = logging.getLogger('log')
		fh = logging.FileHandler(filename)
		UtilzLog.setHandler(fh)

	@staticmethod
	def p(message = "", level = 3, preset = "info"):
		if not isinstance(level, int):
			raise error("Level must be an integer, `%s' given instead." % (str(level)))

		# Ignore if this level is not considered
		if level > UtilzLog.verboseLevel:
			return

		if UtilzLog.presets.has_key(preset):
			colorWrap = UtilzLog.presets[preset]['colorWrap']
			loggingType = UtilzLog.presets[preset]['loggingType']
			if loggingType == "info":
				fct = logging.getLogger('log').info
			elif loggingType == "error":
				fct = logging.getLogger('log').error
			elif loggingType == "warn":
				fct = logging.getLogger('log').warn
			elif loggingType == "debug":
				fct = logging.getLogger('log').debug
			else:
				raise error("Unknown logging type `%s'." % (str(loggingType)))
		else:
			raise error("Unknown preset `%s'." % (str(preset)))

		# If a hook is defined
		hooks = UtilzLog.hooks
		if hooks.has_key(preset):
			message = hooks[preset][0](preset, str(message), hooks[preset][1])

		# Wrap the message with the color
		message = colorWrap % (str(message))

		# Call the function
		fct(message, extra={"level": level, "preset": preset})

# Inistialize the logging instance
UtilzLog.log = UtilzLog()

class error(Exception):
	def __init__(self, message):
		self.message = message
		UtilzLog.error(message, UtilzLog.LOG_DEFAULT_LEVEL_ERROR)
	def __str__(self):
		return str(self.message)
