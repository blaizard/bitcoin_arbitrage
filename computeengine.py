#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.port.btce import *
from strategies.triangularArbitrage import *
from strategies.stableCurrency import *
from bot import *
from privateConfig import *

def hookLog(preset, message, args = None):
	if preset == "display":
		try:
			f = open('/var/www/html/display.txt', 'w')
			f.write(message)
			f.close()
		except:
			pass

	return message

if __name__ == "__main__":

	# Set the verbosity level
	UtilzLog.setVerbosity(1)

	# Disble simulation mode
	# !! Warning !! This will deal with the real money
	Exchange.disableSimulationMode()

	# Set the log hook
	UtilzLog.setHook("display", hookLog)

	config = {}
	config['apiKey'] = BTCE_APIKEY
	config['apiSecret'] = BTCE_APISECRET

	btce = ExchangeBTCE(config)

	b = Bot({
		'exchanges': [btce],
		'algorithms': [triangularArbitrage, stableCurrency],
		'debug': False
	})
	b.run()
