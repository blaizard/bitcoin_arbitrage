#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

from exchanges.port.btce import *
from strategies.triangularArbitrage import *
from bot import *

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
	UtilzLog.setHook(hookLog)

	config = {}
	config['apiKey'] = "34UGXSQD-UEGIFE5Q-TOCSA3LO-CGXLZBQO-NT3YTL9X"
	config['apiSecret'] = "b79fbc82b00d1f597fe7703a896ac50b3276e3335c6ca63fbb130672acaef75a"

	btce = ExchangeBTCE(config)

	b = Bot({
		'exchanges': [btce],
		'algorithms': [triangularArbitrage],
		'debug': False
	})
	b.run()
