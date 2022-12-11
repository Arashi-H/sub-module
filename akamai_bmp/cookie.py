# ====================== - ======================== #
#                   Class: CookieGen                #
#          Usage: Simplify SensorData generation    #
# ======================= - ======================= #
from discord_webhook.webhook import send_webhook
from colorama import Fore, Style
from threading import Thread
import requests
import logging
import json
import time


class CookieGen(Thread):

	def __init__(self, api_key: str):
		# Super Construct for Threaded Classes
		super(CookieGen, self).__init__()

		self.api_key = api_key
		self.authed = False
		self.sensor_data = []

		# Test if Akamai API is available
		logging.info(f'Initializing Connection to Akamai API')
		try:
			_response = requests.get(
				url='https://bmp.sneakersgate.xyz/test',
				headers=
				{
					'accept': 'application/json',
					'Authorization': self.api_key,
				},
				timeout=10
			)

			if 'success' in _response.text:
				logging.info(f'Connected to Akamai API successfully')
				self.authed = True
			else:
				logging.critical(f'Initializing to Akamai API failed')

		except (Exception, requests.exceptions.ReadTimeout) as _e:

			logging.critical(f'Initializing to Akamai API failed | {str(_e)}')

	# ======================================== #
	# This function will generate a new Cookie #
	# ======================================== #
	def generateCookie(self):

		logging.info('Getting new Sensor Data Cookie')

		if self.authed:
			_rawResp = requests.get(
				url='https://bmp.sneakersgate.xyz/api/public/bmp/client/v1/createSensor',
				params={
					'packageName': 'com.myntra.Myntra',
					'bmpversion': '3.2.6',
					'manufacturer': 'iphone',
				},
				headers={
					'accept': 'application/json',
					'Authorization': self.api_key,
				}
			)

			# Extract Cookie from Response
			try:
				_sensorData = json.loads(_rawResp.text)['sensor_data']
				logging.info(f'SENSOR DATA: {_sensorData}')
				return _sensorData

			except (Exception, ValueError):
				time.sleep(60)
				return self.generateCookie()

		else:
			logging.critical(f'You are not authenticated!')
			input()

	# ================================================ #
	# This function will create a new Cookie to return #
	# ================================================ #
	def getSensorData(self):
		if len(self.sensor_data) == 0:
			_sensor = self.generateCookie()

			return _sensor[0]["sensor"]

		else:
			try:
				return self.sensor_data.pop()[0]["sensor"]

			# We put a new Cookie into our storage
			finally:
				self.sensor_data.append(self.generateCookie())
