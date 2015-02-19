#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

import re
import socket
import urllib
import urllib2
import unicodedata
import inspect
import json

from log import *
from object import *

class UtilzData(object):
	"""
	Utility functions for data
	"""
	proxy = None

	def __init__(self, data = ""):
		self.data = data

	@classmethod
	def setProxy(cls, proxy):
		"""
		Set a proxy
		"""
		cls.proxy = proxy

	def get(self):
		"""
		Return the value
		"""
		return self.data

	def fromJSON(self):
		"""
		Convert the data to a Json object
		"""
		self.data = json.loads(self.data)
		# To enable chainability
		return self

	def fetch(self, options):
		"""
		Fetch data from any location
		"""
		data = ""
		# If it needs to be fetched from a file
		if options.has_key("file"):
			UtilzLog.info("Fetching data from file: `%s'" % (str(options["file"])))
			data = str(read_file(options["file"]))
		# If it needs to be fetched from a string
		elif options.has_key("string"):
			UtilzLog.info("Fetching data from string: `%s'" % ((str(options["string"])[:75] + '..') if len(str(options["string"])) > 75 else str(options["string"])))
			data = str(options["string"])
		# If the data need to be fetched from a URL
		elif options.has_key("url"):
			proxy = self.proxy
			data = ""
			timeout = 10

			# Default headers
			headers = {
				'Accept': '*/*',
				'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
				'Accept-Language': 'en-US,en;q=0.8',
				'Proxy-Connection': 'keep-alive',
				'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.102 Safari/537.36'
			}

			# Handle proxy
			if options.has_key("proxy"):
				proxy = options["proxy"]
			# Set the proxy if needed
			if proxy != None:
				proxy = urllib2.ProxyHandler(proxy)
				opener = urllib2.build_opener(proxy)
				urllib2.install_opener(opener)

			data = None
			# Handle POST data
			if options.has_key("post"):
				if isinstance(options['post'], str):
					data = options['post']
				else:
					data = urllib.urlencode(options['post'])
				headers["Content-Type"] = 'application/x-www-form-urlencoded';
				headers["Content-Length"] = len(data);

			# Handle XML data
			elif options.has_key("xml"):
				data = options['xml']
				headers["Content-Type"] = 'application/xml';
				headers["Content-Length"] = len(data);

			# Handle headers
			if options.has_key("headers"):
				headers.update(options['headers'])

			# Build the request
			request = urllib2.Request(str(options["url"]), data, headers)

			# Handle timeout in seconds
			if options.has_key("timeout"):
				timeout = options['timeout']
			# Build the request and process
			UtilzLog.info("Fetching data from url: `%s'" % (str(options["url"])))
			try:
				response = urllib2.urlopen(request, timeout = timeout)
			except urllib2.URLError, e:
				raise error("Error while retreiving the page `%s' (timeout [%is]): %r: %s" % (str(options["url"]), timeout, e, str(e)))
			except socket.timeout:
				raise error("Timeout error (%is)" % (timeout))
			data = str(response.read())
		# Apply encoding if any
		if options.has_key("encoding"):
			data = data.decode(options["encoding"], 'replace')
		data = unicode(data)
		# At this point, data must be in unicode
		# Character transaltion table for some strange unicode charcaters
		data = unicodedata.normalize('NFKD', data)
		data = data.replace(u"\u2013", u"-")
		# Convert to ascii
		data = data.encode('ascii', 'replace')
		# Save the data
		self.data = data
		# To enable chainability
		return self
