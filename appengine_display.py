#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

import lib.cloudstorage as gcs
import webapp2

class MainPage(webapp2.RequestHandler):
	def get(self):
		try:
			f = gcs.open("/arbitrageblaise.appspot.com/balance.txt", 'r')
			if f == None:
				raise
			data = f.read()
			if data == "":
				raise
			self.response.headers['Content-Type'] = 'text/html'
			self.response.write("<html><head><meta http-equiv=\"refresh\" content=\"1\"></head><body><pre>%s</pre></body></html>" % (data))
		except Exception as e:
			self.response.headers['Content-Type'] = 'text/html'
			self.response.write("<html><head><meta http-equiv=\"refresh\" content=\"1\"></head><body>Reloading...</body></html>")

application = webapp2.WSGIApplication([
	('/display', MainPage),
], debug = True)
