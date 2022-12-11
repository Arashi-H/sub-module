import logging
from threading import Thread
import numpy as np
import os
import cv2
import base64
import time
import json
from datetime import datetime, timedelta
from colorama import Style, Fore


class CaptchaEngine(Thread):
	def __init__(self, myntraSession, solveAmount):

		super(CaptchaEngine, self).__init__()
		_curr_time_str = f'{Fore.YELLOW}[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]{Fore.RESET}'
		print(f'{_curr_time_str}{Fore.YELLOW} Starting captchaEngine')

		self.captchaBank = []
		self.myntraSession = myntraSession
		self.solveAmount = solveAmount

		__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
		self.label = "0123456789"
		configPath = os.path.join(__location__, "data\yolov4_captcha.cfg")
		weightPath = os.path.join(__location__, "data\yolov4_captcha_last.weights")
		self.net = cv2.dnn.readNet(configPath, weightPath)
		self.layer = self.net.getUnconnectedOutLayersNames()

	def updateSession(self, _cookies, _headers):
		self.myntraSession.cookies = _cookies
		self.myntraSession.headers = _headers

	def base64_cv2(self, base64_str):
		im_bytes = base64.b64decode(base64_str)
		nparr = np.fromstring(im_bytes, np.uint8)
		image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
		return image

	def cv2_alpha_white(self, cvimg):
		h, w, c = cvimg.shape
		B, G, R, A = cv2.split(cvimg)
		alpha = A / 255
		R = (255 * (1 - alpha) + R * alpha).astype(np.uint8)
		G = (255 * (1 - alpha) + G * alpha).astype(np.uint8)
		B = (255 * (1 - alpha) + B * alpha).astype(np.uint8)
		new_img = cv2.merge((B, G, R))
		return new_img

	def solve(self, image):
		def get_key_x(item):
			return item[1]

		H, W, _ = image.shape
		blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416), swapRB=True, crop=False)
		self.net.setInput(blob)
		layerOutputs = self.net.forward(self.layer)

		boxes = []
		confidences = []
		classIDs = []
		for output in layerOutputs:
			for detection in output:
				scores = detection[5:]
				classID = np.argmax(scores)
				confidence = scores[classID]
				if confidence > 0.5:
					box = detection[0:4] * np.array([W, H, W, H])
					(centerX, centerY, width, height) = box.astype("int")
					x = int(centerX - (width / 2))
					y = int(centerY - (height / 2))
					boxes.append([x, y, int(width), int(height)])
					confidences.append(float(confidence))
					classIDs.append(classID)

		idxs = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.3)

		retBox = []
		retCL = []
		retConf = []
		if len(idxs) > 0:
			for i in idxs.flatten():
				retBox.append(boxes[i])
				retCL.append(classIDs[i])
				retConf.append(confidences[i])
		info = []
		text = ''
		for b, cl, cf in zip(retBox, retCL, retConf):
			x, y, w, h = b
			info.append((self.label[cl], x, y, w, h, cf))
		# image = cv2.putText(image, self.label[cl], (x, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

		info = sorted(info, key=get_key_x)
		for d in info:
			lbl, x, y, w, h, _ = d
			# print(lbl)
			text = text + lbl
		return text

	def myntraGetCaptcha(self):
		return self.myntraSession.get(
			url='https://www.myntra.com/gateway/v1/captcha',
			headers={
				'Host': 'www.myntra.com',
				'accept': 'application/json',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'accept-language': 'en-us',
				'x-meta-app': 'channel=web',
				'x-sec-clge-req-type': 'ajax',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'referer': 'https://www.myntra.com/checkout/payment',
				'x-myntraweb': 'Yes',
			}
		)

	def solveMyntraCaptcha(self):
		logging.info(f'Solving Captcha...')

		for i in range(int(self.solveAmount)):
			time.sleep(1)
			# Get captcha
			_captchaData = self.myntraGetCaptcha()

			# Get Data for captcha
			try:
				_captcha_raw = json.loads(_captchaData.text)
				_captchaId = _captcha_raw['id']
				_captchaImage_b64 = _captcha_raw['image']

			except (ValueError, Exception) as _e:
				logging.info(f'Error getting Captcha data! | {str(_e)}')
				return self.solveMyntraCaptcha()

			# Solve using Captcha Engine

			# Read captcha and write to file
			try:

				_text = self.solve_b64(_captchaImage_b64)

				logging.info(f'CAPTCHA [#{_captchaId}] -> {_text}')
				self.captchaBank.append(
					{
						'captchaId': _captchaId,
						'captchaText': _text,
						'timestamp': datetime.now()
					}
				)

			except (Exception, ValueError) as _e:
				logging.critical(f'Error solving Captcha! | {str(_e)}')

			return

	def solve_b64(self, base64):
		arr = base64.split(',')
		base64 = arr[1]
		cvimg = self.base64_cv2(base64)
		cvimg = self.cv2_alpha_white(cvimg)
		return self.solve(cvimg)

	def solve_file(self, image_path):
		cvimg = cv2.imread(image_path)
		return self.solve(cvimg)

	def run(self):
		self.solveMyntraCaptcha()

		while True:
			if len(self.captchaBank) < self.solveAmount:
				logging.info(f'Almost no captchas left -> Solving new one')
				self.solveMyntraCaptcha()

			for captcha in self.captchaBank:
				if (datetime.now() - captcha['timestamp']) > timedelta(minutes=2):
					self.captchaBank.remove(captcha)

					logging.info(f'Deleted expired captcha! -> Solving new one')
					self.solveMyntraCaptcha()

			time.sleep(1)

	def getCaptcha(self):
		return self.captchaBank.pop()
