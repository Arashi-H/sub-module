# ====================== - ======================== #
#                 Class: MyntraTask                 #
#          Usage: Simplify SensorData generation    #
# ======================= - ======================= #

from discord_webhook.webhook import send_webhook
from captcha.solver import CaptchaEngine
from akamai_bmp.cookie import CookieGen
from colorama import Fore, Style, init
from datetime import datetime, timedelta

import traceback
import threading
import requests
import logging
import base64
import time
import json
import uuid
import csv
import sys
import cv2

DEBUG = True

init()

# Create Logging file
CURR_LOGFILE = datetime.now().strftime("%d_%m_%Y %H_%M_%S")
logging.basicConfig(filename=f'log/myntra_{CURR_LOGFILE}.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s MYNTRA  %(message)s')


# Enable for uncaught_exception_handler
def uncaught_exception_handler(exc_type, exc_value, exc_traceback):
	if issubclass(exc_type, Exception):
		print(Fore.RED + "Unknown Error!" + str(exc_type) + traceback.format_exc() + Fore.RESET)
		logging.critical(traceback.format_exc())

	if exc_type == KeyboardInterrupt:
		logging.critical("CTRL+C was used to close the Bot")
		time.sleep(2)
		os._exit(0)

	logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
	return


sys.excepthook = uncaught_exception_handler


class MyntraTask(threading.Thread):

	def __init__(self, login_phone: str, login_password: str, _size_preference: int, _run: int):

		self.prodStock = None
		self.prodSize = None
		print(f'{Fore.YELLOW}Initializing Task [{login_phone}]{Style.RESET_ALL}')

		logging.info('Initializing Myntra Task')

		super(MyntraTask, self).__init__()

		self.cookieGen = CookieGen('4eafb38f34b84e25af80580325df1e48')

		logging.info('Reading config file')

		try:
			with open('config.json', 'r') as _configFile:
				json_settings = json.loads(_configFile.read())

				self.login_phone = login_phone
				self.login_password = login_password
				self.delay = float(json_settings["DELAY"])
				self.webhook_url = json_settings["WEBHOOK"]
				self.preSolve_Amount = json_settings["CAPTCHA_AMOUNT"]
				self.preferenceSizes = _size_preference

				logging.info(f'Config File read')

		except (ValueError, Exception) as _e:
			print(f'{Fore.RED}Error Reading config file ({str(_e)})... Press enter to close the Tool{Fore.RESET}')
			input()
			exit()

		self.myntraSession = requests.Session()
		self.myntraSession.headers[
			'user-agent'] = 'Myntra/4.2204.2 (iPhone; iOS 14.8; Scale/2.00)'

		self.captchaEngine = None

		self.captchaBank = []

		self.running = _run
		self.uidx = None
		self.userID = None
		self.cartID = None
		self.prodName = None
		self.prodPrice = None
		self.prodImage = None
		self.addressID = None
		self.loginToken = None

	def consoleLog(self, _msg):

		logging.info(f'[{self.login_phone}] {_msg[5:]}')

		_phoneNum = f'{Style.BRIGHT}{self.login_phone[-4:]}{Style.RESET_ALL}'
		_curr_time_str = f'{Fore.YELLOW}[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]{Fore.RESET}'
		print(f'{_curr_time_str} [...{_phoneNum}] {_msg}{Style.RESET_ALL}')

	def getSensorData(self):
		tries = 0
		sensor_data = self.cookieGen.getSensorData()
		while not sensor_data:
			tries += 1
			sensor_data = self.cookieGen.getSensorData()
			if tries > 2:
				self.consoleLog(f'{Fore.RED}Error getting sensor data. Stopping')
				send_webhook(
					self.webhook_url,
					{
						"content": None,
						"embeds": [
							{
								"title": "Error getting sensor data",
								"description": "Please check the log",
								"color": 6356992,
								"footer": {
									"text": "Myntra Bot",
									"icon_url": "https://logos-world.net/wp-content/uploads/2021/02/New-Myntra-Logo.png"
								},
								"timestamp": datetime.utcnow().isoformat(),
							}
						],
						"username": "Myntra Bot",
						"avatar_url": "https://res.cloudinary.com/crunchbase-production/image/upload/c_lpad,f_auto,q_auto:eco,dpr_1/v1499793144/wq1zrsfvi5pep2zwyxyi.png",
						"attachments": []
					}
				)
				input()

		return sensor_data

	def myntraGetAtToken(self):
		return (
			self.myntraSession.get(
				url='https://api.myntra.com/auth/v1/token',
				headers={
					'Host': 'api.myntra.com',
					'x-device-state': 'brand=Apple; connectionType=UNKNOWN; model=iPhone 7;',
					'accept': 'application/json',
					'x-myntra-app': 'appFamily=MyntraRetailiOS; appVersion=4.2204.2; appBuild=10493; deviceCategory=iPhone; osVersion=14.8; installationID=712A9679-D700-4705-BECE-AF9C65F26AA7; sessionID=712A9679-D700-4705-BECE-AF9C65F26AA7/2022-07-05T21:15:11.237Z; deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3; bundleVersion=1.0.0;',
					'clientid': 'myntra-02d7dec5-8a00-4c74-9cf7-9d62dbea5e61',
					'x-location-context': 'pincode=; source=',
					'x-acf-sensor-data': self.getSensorData(),
					'accept-language': 'en-DE;q=1, de-DE;q=0.9',
					'ignore-refresh': 'true',
					'x-slot-mode': 'disbaled',
					'user-agent': 'Myntra/4.2204.2 (iPhone; iOS 14.8; Scale/2.00)',
				}
			)
		)

	def myntraRefreshSession(self):
		return (
			self.myntraSession.get(
				url='https://api.myntra.com/auth/v1/refresh',
				headers={
					'Host': 'api.myntra.com',
					'x-device-state': 'brand=Apple; connectionType=WIFI; model=iPhone 7;',
					'accept': 'application/json',
					'x-myntra-app': 'appFamily=MyntraRetailiOS; appVersion=4.2204.2; appBuild=10493; deviceCategory=iPhone; osVersion=14.8; installationID=A863686C-1E55-4CF0-B7D5-E4448C193A36; customerID=bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2; sessionID=A863686C-1E55-4CF0-B7D5-E4448C193A36/2022-07-08T03:15:39.881Z; deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3; bundleVersion=1.0.2;',
					'clientid': 'myntra-02d7dec5-8a00-4c74-9cf7-9d62dbea5e61',
					'user-state': 'CUSTOMER',
					'x-location-context': 'pincode=401107; source=USER',
					'x-acf-sensor-data': self.getSensorData(),
					'accept-language': 'en-DE;q=1, de-DE;q=0.9',
					'ignore-refresh': 'true',
					'x-slot-mode': 'disbaled',
					'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				}
			)
		)

	def myntraLogin(self):
		return (
			self.myntraSession.post(
				url='https://api.myntra.com/auth/v1/phonelogin',
				headers={
					'Host': 'api.myntra.com',
					'x-device-state': 'brand=Apple; connectionType=WIFI; model=iPhone 7;',
					'accept': 'application/json',
					'x-myntra-app': 'appFamily=MyntraRetailiOS; appVersion=4.2204.2; appBuild=10493; deviceCategory=iPhone; osVersion=14.8; installationID=1F07EB77-AF22-49D9-BED1-ED43D8C4E61A; customerID=bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2; sessionID=1F07EB77-AF22-49D9-BED1-ED43D8C4E61A/2022-07-04T21:40:31.144Z; deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3; bundleVersion=1.0.2;',
					'user-state': 'NEW_USER',
					'x-location-context': 'pincode=; source=',
					'accept-language': 'en-DE;q=1, de-DE;q=0.9',
					'x-acf-sensor-data': self.getSensorData(),
					'ignore-refresh': 'true',
					'x-slot-mode': 'disbaled',
					'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
					'x-myntra-abtest': '1737=27; 1681=27; 1076=26; 1069=1071; 1610=27; 1639=1824; 1780=48; 1590=27; 1048=2; 1098=27; 1055=27; 1625=27; 1682=27; 1478=27; 1752=26; 1077=27; 1724=27; 1851=26; 1056=27; 1049=2; 1063=27; 1619=48; 1753=26; 1809=1810; 775=777; 803=27; 1042=1046; 201=27; 1035=2; 1852=26; 1775=26; 482=27; 1064=27; 1057=1059; 1444=27; 1627=27; 1711=27; 1797=1798; 1634=27; 1050=27; 1113=27; 140=27; 1500=27; 1663=27; 1290=27; 1536=26; 1853=27; 1065=27; 1452=27; 1642=27; 1495=203; 1051=26; 1784=245; 1847=1848; 1073=27; 1143=27; 1509=27; 143=145; 1052=2; 1017=27; 1707=843; 1841=7; 1039=2; 1060=47; 748=749; 1469=27; 1793=1613; 1068=27; 1075=27; 567=27; 1645=27; 1828=26; 1842=1732; 1047=27; 1054=26; 1061=1062; 1554=27',
				},
				json={
					'phoneNumber': self.login_phone,
					'accessKey': self.login_password,
				})
		)

	def myntraGetWishList(self):
		return self.myntraSession.get(
			url='https://api.myntra.com/v1/wishlists/default',
			params={
				'offset': '0',
				'pageSize': '40',
			},
			headers={
				'Host': 'api.myntra.com',
				'x-device-state': 'brand=Apple; connectionType=WIFI;',
				'accept': 'application/json',
				'user-state': 'NEW_USER',
				'x-location-context': 'pincode=; source=',
				'accept-language': 'en-DE;q=1, de-DE;q=0.9',
				'ignore-refresh': 'true',
				'x-slot-mode': 'disbaled',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
			}
		)

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

	def myntraATC(self, styleID: int, sellerPartnerId: int, skuId: int):
		return self.myntraSession.post(
			url='https://api.myntra.com/v1/cart/default/add',
			headers={
				'Host': 'api.myntra.com',
				'x-device-state': 'brand=Apple; connectionType=WIFI;',
				'accept': 'application/json',
				'user-state': 'NEW_USER',
				'x-location-context': 'pincode=; source=',
				'accept-language': 'en-DE;q=1, de-DE;q=0.9',
				'ignore-refresh': 'true',
				'x-slot-mode': 'disbaled',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'x-myntra-abtest': '1057=1059; 1850=27; 1540=1720; 1069=1071; 1724=27; 1035=2; 1793=1613; 1610=27; 1851=26; 1828=26; 1047=27; 1495=203; 1645=27; 1737=27; 1852=26; 1048=2; 1634=27; 748=749; 1841=7; 1060=47; 1554=27; 1738=48; 1290=27; 1853=27; 1049=2; 1784=245; 140=27; 1681=27; 1842=1732; 1509=27; 1061=1062; 1796=7; 1050=27; 1452=27; 1073=27; 1590=27; 1682=27; 775=777; 1039=2; 1625=27; 1797=1798; 143=145; 1809=1810; 1051=26; 1143=27; 1752=26; 1017=27; 1063=27; 1775=26; 1500=27; 1833=351; 1029=27; 1052=2; 1075=27; 1707=843; 1098=27; 1753=26; 1064=27; 1776=26; 482=27; 1627=27; 1076=26; 1478=27; 1639=1824; 1042=1046; 1444=27; 1536=26; 1065=27; 1054=26; 1077=27; 1663=27; 1514=1763; 1847=1848; 803=27; 1055=27; 1113=27; 1469=27; 567=27; 959=1198; 1056=27; 1699=8; 1619=48; 1642=27; 1711=27; 1780=48; 1068=27',
			},
			json=[
				{
					'quantity': 1,
					'id': styleID,
					'sellerPartnerId': sellerPartnerId,
					'skuId': skuId,
				},
			]
		)

	def myntraGetCart(self):
		return self.myntraSession.get(
			url='https://api.myntra.com/v1/cart/default',
			headers={
				'Host': 'api.myntra.com',
				'x-device-state': 'brand=Apple; connectionType=WIFI;',
				'accept': 'application/json',
				'user-state': 'NEW_USER',
				'x-location-context': 'pincode=; source=',
				'accept-language': 'en-DE;q=1, de-DE;q=0.9',
				'ignore-refresh': 'true',
				'x-slot-mode': 'disbaled',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'x-myntra-abtest': '1057=1059; 1850=27; 1540=1720; 1069=1071; 1724=27; 1035=2; 1793=1613; 1610=27; 1851=26; 1828=26; 1047=27; 1495=203; 1645=27; 1737=27; 1852=26; 1048=2; 1634=27; 748=749; 1841=7; 1060=47; 1554=27; 1738=48; 1290=27; 1853=27; 1049=2; 1784=245; 140=27; 1681=27; 1842=1732; 1509=27; 1061=1062; 1796=7; 1050=27; 1452=27; 1073=27; 1590=27; 1682=27; 775=777; 1039=2; 1625=27; 1797=1798; 143=145; 1809=1810; 1051=26; 1143=27; 1752=26; 1017=27; 1063=27; 1775=26; 1500=27; 1833=351; 1029=27; 1052=2; 1075=27; 1707=843; 1098=27; 1753=26; 1064=27; 1776=26; 482=27; 1627=27; 1076=26; 1478=27; 1639=1824; 1042=1046; 1444=27; 1536=26; 1065=27; 1054=26; 1077=27; 1663=27; 1514=1763; 1847=1848; 803=27; 1055=27; 1113=27; 1469=27; 567=27; 959=1198; 1056=27; 1699=8; 1619=48; 1642=27; 1711=27; 1780=48; 1068=27',
			}
		)

	def myntraGetCheckoutCart(self):
		return self.myntraSession.get(
			url='https://www.myntra.com/checkout/cart',
			headers={
				'Host': 'www.myntra.com',
				'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
				'user-state': 'CUSTOMER',
				'x-location-context': 'pincode:401107|addressId:383993973',
				'x-location-context-api': 'pincode:401107|source:USER|ttl:1440',
				'accept-language': 'en-us',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'x-myntra-abtest': 'sizeselectorpill.ui=enabled; pdp.alterations.display=enabled; wallet=enabled; pdp.hourLevelDelivery=enabled; search.additionalInfo=test; pdp.ios.react.v1=enabled; shortlist.list.click=default; topnav_quicklinks_50-50=VariantA; eid-gifvsstatic=VariantA; pdp.notify.me=disabled; myorders.npstouchpoint=Test; search_as_number_suggestions=bucket_6_2; cart.views=enabled; checkout.selective=enabled; mLive.shopAllText=disabled; reco.feed.v1=enabled; list.interactive.variant=default; product.raters.listview=enabled; pps=enabled; search.sampling=enabled; lgp.beauty=jpg; kids.sizechart=disabled; plp.bodyshape.filter=enabled; tags.low_return=enabled; pdp.Viewsimilartext=enabled; nav.store=disabled; cart.couponexpirytimer=enabled; mLive.viewsimilar=enabled; product.ugcfashion=enabledratings; sizereco.confidencelevel=B; pdp.details=table; pdp.multiple.coupons=enabled1; checkout.attachedProducts=enabled; lgp.timeline.cardloadevent=enabled; pdp.trust.highlight=enabled; pdp.coupontimer=enabled; usercontext.on=false; dynamic.pla.slots=control; pdp.crosssell.atc.permanent=disabled; search_symspell=control; Cart.strikeoffMRP=enabled; cart.fomoinventory=enabled; nav.links=store; rn.update=default; pdp.studiowidget.pos=enabled; search.visual=enabled; virtualTrialRoom=disabled; app.home.screen.v3=layout_engine_feed_v3_with_fix; plp.valueprop_vs_discount_2=Test1; mymyntra.armor=enabled; checkout.couponUpsell=enabled; pdp.expiry.date=enabled; pdp.video=disabled; pdp.insider.calloutacc=disabled; pdp.ios.livephoto=disabled; address.v2=enabled; pdp.color.variants.selector=enabled; pdp.react.colorselection=enabled; pdp.ios.react=enabled; checkout.donation=enabled; wishlist.ratings=control; checkout.payment.dope=ucretryfirst; pdp.faster.delivery.nudge=enabled; ordersSearch=VariantB; config.bucket=regular; search.speed.mexpress=VariantD; lgp.rollout=enabled; pdp.forum=enabled; lgp.stratnav=strat; mLive.immersiveMode=disabled; mLive.plpView=enabled; pdp.influencer.content=enabled; android.looksoms=flatshots; nudges.home.search=enabled; lgp.featurednav=disabled; lgp.rollout.ios=enabled; list.short.videos=enabled_default; lgp.stylecast=disabledGroup; pdp.earlybird=enabled; mLive.atcFeedback=enabled; ios.profile.fab=default; pdp.lowestprice=strip; cart.cartfiller=bnb-cart; rn.update.ios=default; wishlist.bagcount=enabled; pdp.similar.rpi=enabled',
			},
			cookies={
				'xma': self.myntraSession.headers,
				'_mxab_': 'checkout.selective%3Denabled%3Bconfig.bucket%3Dregular%3Bcheckout.couponUpsell%3Denabled%3Bcheckout.attachedProducts%3Denabled%3Bcheckout.payment.dope%3Ducretryfirst%3Bcheckout.donation%3Denabled%3Bpdp.expiry.date%3Denabled%3Bcart.fomoinventory%3Denabled%3Bcart.cartfiller%3Dbnb-cart%3Bcart.views%3Denabled%3Bcart.couponexpirytimer%3Denabled%3BCart.strikeoffMRP%3Denabled%3Bsearch.speed.mexpress%3DVariantD',
				'mynt-loc-src': 'expiry%3A604800000%7Csource%3AUSER',
				'mynt-ulc': 'pincode:401107|addressId:383993973',
				'mynt-ulc-api': 'pincode%3A401107',
				'oai': '383993973',
				'oaui': '383993973:1',
				'ru': 'VC9hMERiYF5qVE5BERt6CwUDbWwGEV5DXVdsJF84SkVGGRdxXhNcFBsvcy5wRkAwIzI2NTE5OTczMTQkMg%3D%3D.f1421fdb70f1fa04fc01c676d6079d48',
				'user_uuid': 'bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2',
				'utrid': 'B31iYEhpZlNyD05PHgVAMCMyNjUxOTk3MzE0JDI%3D.79e271da2713005045178f633c57fe3a',
				'ftc': 'false',
				'ak_RT': '"z=1&dm=myntra.com&si=cb9e8f00-7b96-4202-a3a1-0a10d660c850&ss=l564tdbz&sl=1&tt=1ez&rl=1&ld=1jf"',
				'utm_track_v1': '%7B%22utm_source%22%3A%22direct%22%2C%22utm_medium%22%3A%22direct%22%2C%22trackstart%22%3A1656902245%2C%22trackend%22%3A1656902305%7D',
				'_ga': 'GA1.2.196083675.1656894570',
				'_gid': 'GA1.2.807698332.1656894570',
				'__cab': 'cart.fsexp%3D',
				'_cf': 'default',
				'AKA_A2': 'A',
				'_pv': 'default',
				'ismd': '1',
				'sc_tt': 'true',
				'_loms': 'flatshots',
				'webVitals': 'true',
				'ilgim': 'true',
			}
		)

	def myntraGetAddress(self):
		return self.myntraSession.get(
			url='https://www.myntra.com/gateway/v2/addresses',
			headers={
				'Host': 'www.myntra.com',
				'content-type': 'application/x-www-form-urlencoded',
				'accept': '*/*',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'accept-language': 'en-us',
				'x-meta-app': 'channel=web',
				'x-sec-clge-req-type': 'ajax',
				'x-myntra-abtest': 'checkout.selective=enabled;config.bucket=regular;checkout.couponUpsell=enabled;checkout.attachedProducts=enabled;checkout.payment.dope=ucretryfirst;checkout.donation=enabled;pdp.expiry.date=enabled;cart.fomoinventory=enabled;cart.cartfiller=bnb-cart;cart.views=enabled;cart.couponexpirytimer=enabled;Cart.strikeoffMRP=enabled;search.speed.mexpress=VariantD;checkout.cartmerge=enabled;',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'referer': 'https://www.myntra.com/checkout/address',
				'x-myntraweb': 'Yes',
			},
		)

	def myntraPutAddress(self):
		return self.myntraSession.put(
			url=f'https://www.myntra.com/gateway/v1/cart/default/address?unifiedAddressId={self.addressID}:1&addressId={self.addressID}',
			headers={
				'Host': 'www.myntra.com',
				'accept': '*/*',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'pagesource': 'address',
				'x-meta-app': 'channel=web',
				'x-sec-clge-req-type': 'ajax',
				'accept-language': 'en-us',
				'origin': 'https://www.myntra.com',
				'x-myntra-abtest': 'checkout.selective=enabled;config.bucket=regular;checkout.couponUpsell=enabled;checkout.attachedProducts=enabled;checkout.payment.dope=ucretryfirst;checkout.donation=enabled;pdp.expiry.date=enabled;cart.fomoinventory=enabled;cart.cartfiller=bnb-cart;cart.views=enabled;cart.couponexpirytimer=enabled;Cart.strikeoffMRP=enabled;search.speed.mexpress=VariantD;checkout.cartmerge=enabled;',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'referer': 'https://www.myntra.com/checkout/address',
				'x-myntraweb': 'Yes',
				'Content-Type': 'application/x-www-form-urlencoded',
			}
		)

	def myntraCSRF(self):
		return self.myntraSession.post(
			url='https://pps.myntra.com/myntra-payment-plan-service/v3/paymentInstruments',
			headers={
				'Host': 'pps.myntra.com',
				'referer': 'https://www.myntra.com/checkout/payment',
				'x-requested-with': 'browser',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'client': 'checkout',
				'origin': 'https://www.myntra.com',
				'x-myntraweb': 'Yes',
				'paynow-version': 'v3',
				'version': '1.0',
				'x-meta-app': 'channel=web',
				'x-myntra-abtest': 'checkout.selective=enabled;config.bucket=regular;checkout.couponUpsell=enabled;checkout.attachedProducts=enabled;checkout.payment.dope=ucretryfirst;checkout.donation=enabled;pdp.expiry.date=enabled;cart.fomoinventory=enabled;cart.cartfiller=bnb-cart;cart.views=enabled;cart.couponexpirytimer=enabled;Cart.strikeoffMRP=enabled;search.speed.mexpress=VariantD;checkout.cartmerge=enabled;',
				'accept-language': 'en-us',
				'x-location-context': 'pincode=401107;source=USER',
				'accept': '*/*',
				'xmetaapp': 'appFamily=MyntraRetailiOS, appVersion=4.2204.2, appBuild=10493, deviceCategory=iPhone, osVersion=14.8, installationID=4B6FFA82-828D-4CEA-AD40-56F9D8EC554A, customerID=bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2, sessionID=4B6FFA82-828D-4CEA-AD40-56F9D8EC554A/2022-07-02T03:46:07.417Z, deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3, bundleVersion=1.0.2',
				'saved-instruments': 'true',
			},
			cookies={
				'mynt-ulc': f'pincode:401107|addressId:{self.addressID}',
				'mynt-ulc-api': 'pincode%3A401107',
				'oai': '375260354',
				'oaui': '375260354:4'
			},
			json={
				'cartId': self.cartID,
			}
		)

	def myntraGetUser(self):
		return self.myntraSession.get(
			url='https://www.myntra.com/gateway/v1/user/profile',
			headers={
				'Host': 'www.myntra.com',
				'accept': '*/*',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'accept-language': 'en-us',
				'x-meta-app': 'channel=web',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'x-myntraweb': 'Yes',
				'referer': 'https://www.myntra.com/checkout/cart',
			}
		)

	def myntraGetCheckoutProxy(self):
		return self.myntraSession.get(
			url='https://www.myntra.com/checkoutproxy/cartData',
			headers={
				'Host': 'www.myntra.com',
				'accept': '*/*',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'accept-language': 'en-us',
				'x-meta-app': 'channel=web',
				'x-sec-clge-req-type': 'ajax',
				'x-myntra-abtest': 'checkout.selective=enabled;config.bucket=regular;checkout.couponUpsell=enabled;checkout.attachedProducts=enabled;checkout.payment.dope=ucretryfirst;checkout.donation=enabled;pdp.expiry.date=enabled;cart.fomoinventory=enabled;cart.cartfiller=bnb-cart;cart.views=enabled;cart.couponexpirytimer=enabled;Cart.strikeoffMRP=enabled;search.speed.mexpress=VariantD;checkout.cartmerge=enabled;',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'referer': 'https://www.myntra.com/checkout/cart',
			},
			params={
				'cm': 'true',
				'cached': 'false',
				'unselected': 'true',
			}
		)

	def myntraCheckout(self, _captchaData: dict, _csrf: str):
		return self.myntraSession.post(
			url='https://pps.myntra.com/myntra-payment-plan-service/v3/buy',
			headers={
				'Host': 'pps.myntra.com',
				'accept': '*/*',
				'version': '1.0',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'accept-language': 'en-us',
				'x-meta-app': 'channel=web',
				'origin': 'https://www.myntra.com',
				'x-myntra-abtest': 'checkout.selective=enabled;config.bucket=regular;checkout.couponUpsell=enabled;checkout.attachedProducts=enabled;checkout.payment.dope=ucretryfirst;checkout.donation=enabled;pdp.expiry.date=enabled;cart.fomoinventory=enabled;cart.views=enabled;payments.iconrevamp=enabled;search.speed.mexpress=VariantD;app.shop.screen.v3=defaultShop;Convenience_fee_logged_out_user=disabled;pdp.autoapply.newusercoupon=enabled;checkout.paymentOptions.reorderv2=disabled;checkout.cartmerge=enabled;',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'x-myntraweb': 'Yes',
				'referer': 'https://www.myntra.com/checkout/payment',
				'client': 'checkout',
			},
			cookies={
				'xma': 'appFamily=MyntraRetailiOS, appVersion=4.2206.4, appBuild=10498, deviceCategory=iPhone, osVersion=14.8, installationID=592A1432-FC35-423D-94B5-9EEF7D183D66, customerID=8888f1d9.62a1.4fca.98a7.22b2446284b65X50zOEbYW, sessionID=592A1432-FC35-423D-94B5-9EEF7D183D66/2022-08-28T14:18:48.396Z, deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3, appsflyerId=1656551466335-6989396, ruCustomerID=bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2, bundleVersion=1.0.0',
				'mynt-loc-src': 'expiry%3A604800000%7Csource%3AUSER',
				'mynt-ulc': 'pincode:401107|addressId:375260354',
				'mynt-ulc-api': 'pincode%3A401107',
				'ftc': 'false',
			},
			json={
				'captchaId': _captchaData['captchaId'],
				'codCaptcha': _captchaData['captchaText'],
				'amount': self.prodPrice,
				'csrf': _csrf,
				'cartContext': 'default',
				'cartId': self.cartID,
				'clientContext': 'responsive',
				'paymentMethods': 'cod',
				'profile': 'www.myntra.com',
				'xMetaApp': 'appFamily=MyntraRetailiOS, appVersion=4.2206.4, appBuild=10498, deviceCategory=iPhone, osVersion=14.8, installationID=592A1432-FC35-423D-94B5-9EEF7D183D66, customerID=8888f1d9.62a1.4fca.98a7.22b2446284b65X50zOEbYW, sessionID=592A1432-FC35-423D-94B5-9EEF7D183D66/2022-08-28T14:18:48.396Z, deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3, appsflyerId=1656551466335-6989396, ruCustomerID=bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2, bundleVersion=1.0.0',
				'channel': 'iOS',
				'autoGiftCardUsed': '',
				'autoGiftCardAmount': '0',
				'giftcardType': '',
				'myntraCreditEligible': '',
				'myntraCreditAmount': '0',
				'useloyaltypoints': 'N',
			}
		)

	def myntraClrCart(self, _items):
		return self.myntraSession.put(
			url='https://www.myntra.com/gateway/v1/cart/default/remove',
			headers={
				'Host': 'www.myntra.com',
				'accept': '*/*',
				'x-requested-with': 'browser',
				'x-location-context': 'pincode=401107;source=USER',
				'pagesource': 'cart',
				'x-meta-app': 'channel=web',
				'x-sec-clge-req-type': 'ajax',
				'accept-language': 'en-us',
				'origin': 'https://www.myntra.com',
				'x-myntra-abtest': 'checkout.selective=enabled;config.bucket=regular;checkout.couponUpsell=enabled;checkout.attachedProducts=enabled;checkout.payment.dope=ucretryfirst;checkout.donation=enabled;pdp.expiry.date=enabled;cart.fomoinventory=enabled;cart.cartfiller=bnb-cart;cart.views=enabled;cart.couponexpirytimer=enabled;Cart.strikeoffMRP=enabled;search.speed.mexpress=VariantD;checkout.cartmerge=enabled;',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'referer': 'https://www.myntra.com/checkout/cart',
				'x-myntraweb': 'Yes',
			},
			params={
				'unselected': 'true',
			},
			json=_items
		)

	def myntraSetID(self):

		_instID = str(uuid.uuid4()).upper()

		return self.myntraSession.post(
			url=f'https://api.myntra.com/magasin/installation/{_instID}',
			headers={
				'Host': 'api.myntra.com',
				'x-device-state': 'brand=Apple; connectionType=WIFI;',
				'accept': 'application/json',
				'x-myntra-app': 'appFamily=MyntraRetailiOS; appVersion=4.2204.2; appBuild=10493; deviceCategory=iPhone; osVersion=14.8; installationID=1F07EB77-AF22-49D9-BED1-ED43D8C4E61A; customerID=bd6f4228.c688.43b8.89d6.496c3f037313s73iVzVKI2; sessionID=1F07EB77-AF22-49D9-BED1-ED43D8C4E61A/2022-07-04T21:40:31.144Z; deviceID=69A89396-9F9F-491F-9010-B920EBDDD1D3; bundleVersion=1.0.2;',
				'x-location-context': 'pincode=; source=',
				'accept-language': 'en-DE;q=1, de-DE;q=0.9',
				'x-magasin-key': 'e0fc2f477b4b1a118342fbd46ff12ff2',
				'ignore-refresh': 'true',
				'x-slot-mode': 'disbaled',
				'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
			},
			json={
				'isRooted': False,
				'pastOSVersions': [
					'14.8',
				],
				'pastBuildNumbers': [
					'10493',
				],
				'appBuildNumber': '10493',
				'userAgentString': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148; MyntraRetailiPhone/4.2204.2 (iPhone, 375, 667)',
				'deviceId': str(uuid.uuid4()).upper(),
				'deviceType': 'iOS',
				'installationId': _instID,
				'magasinVersion': '1.0.0',
				'deviceName': 'iPhone9,3',
				'appName': 'Myntra',
				'appIdentifier': 'com.myntra.Myntra',
				'OSVersion': '14.8',
				'notificationsDisabled': 0,
				'deviceScreenResolution': '375.000000*667.000000',
				'appVersion': '4.2204.2',
				'deviceManufacturer': 'Apple',
				'deviceTimeZone': 'Europe/Berlin',
				'pushType': 'APNS',
			}

		)

	def checkoutFlow(self):

		startCheckoutTime = datetime.now()

		# Get checkout CSRF Token
		self.consoleLog(f'{Fore.YELLOW}Getting checkout token')
		try:
			_csrf_resp = json.loads(self.myntraCSRF().text)

			if DEBUG:
				logging.info(f'CSRF RESPONSE: {_csrf_resp}')

			if 'out of stock' in str(_csrf_resp):
				self.consoleLog(f'{Fore.RED}Items are sold out')
				return

			elif 'errorReason' in str(_csrf_resp):
				self.consoleLog(f'{Fore.RED}Getting rate limit on checkout')
				time.sleep(self.delay)
				return

			_csrf = _csrf_resp['csrfToken']
			self.loginToken = _csrf_resp['login']

		except (ValueError, Exception) as _e:
			self.consoleLog(f'{Fore.RED}Error getting checkout token! | {str(_e)}')
			logging.critical(f'ERROR GETTING CHECKOUT TOKEN: {str(_csrf_resp)}')
			return self.checkoutFlow()

		self.consoleLog(f'{Fore.YELLOW}Checking out!')

		# Get Captcha from Captcha Bank
		while True:
			try:
				_captchaToUse = self.captchaEngine.getCaptcha()
				if DEBUG:
					logging.info(f'USING CAPTCHA: {_captchaToUse}')
				break
			except (ValueError, Exception) as _e:
				self.captchaEngine.solveMyntraCaptcha()
				self.consoleLog(f'{Fore.RED}Error getting checkout captcha! | {str(_e)}')

		_checkoutResp = self.myntraCheckout(_captchaToUse, _csrf)
		if DEBUG:
			logging.info(f'CHECKOUT RESPONSE: {_checkoutResp.text}')

		logging.info(f'CHECKOUT RESPONSE: {_checkoutResp.text}')

		if 'orderid' in _checkoutResp.text:
			self.consoleLog(f'{Fore.GREEN}Checked out!')

			_orderID = json.loads(_checkoutResp.text)['params']['orderid']

			# Send success webhook
			send_webhook(
				self.webhook_url,
				{
					"content": None,
					"embeds": [
						{
							"title": "Successfully Checked Out!",
							"color": 7069710,
							"fields": [
								{
									"name": "Product",
									"value": f"`{self.prodName}`",
									"inline": True
								},
								{
									"name": "Price",
									"value": f"`₹ {self.prodPrice}`",
									"inline": True
								},
								{
									"name": "Remaining Stock",
									"value": f"`{self.prodStock}`",
									"inline": True
								},
								{
									"name": "Size",
									"value": f"`₹ {self.prodSize}`",
									"inline": True
								},
								{
									"name": "Checkout Time",
									"value": f"`{str(datetime.now() - startCheckoutTime)}`"
								},
								{
									"name": "Order-#",
									"value": f"||{_orderID}||"
								},
								{
									"name": "Phone number",
									"value": f"||{str(self.login_phone)}||"
								}
							],
							"footer": {
								"text": "Myntra Bot",
								"icon_url": "https://logos-world.net/wp-content/uploads/2021/02/New-Myntra-Logo.png"
							},
							"timestamp": datetime.utcnow().isoformat(),
							"thumbnail": {
								"url": self.prodImage
							}
						}
					],
					"username": "Myntra Bot",
					"avatar_url": "https://res.cloudinary.com/crunchbase-production/image/upload/c_lpad,f_auto,q_auto:eco,dpr_1/v1499793144/wq1zrsfvi5pep2zwyxyi.png",
					"attachments": []
				}
			)

		else:

			errorCode = int(json.loads(_checkoutResp.text)['params']['paymentErrorCode'])

			error_ids = {
				1095: "The captcha code you have entered was expired",
				1094: "Payment declined",
				1067: "Order cannot be delivered to your address",
				1005: "Some of the items in your shopping bag just went out of stock",
				1028: "Your bag has updates.",
				1041: "Some of the items in your shopping bag just went out of stock",
			}

			try:
				errorCode = error_ids[errorCode]
			except ValueError:
				errorCode = "Unknown error"

			self.consoleLog(f'{Fore.RED}Error checking out! | {errorCode}')

			# Send failure webhook
			send_webhook(
				self.webhook_url,
				{
					"content": None,
					"embeds": [
						{
							"title": "Error checking out!",
							"color": 14688014,
							"fields": [
								{
									"name": "Product",
									"value": f"`{self.prodName}`",
									"inline": True
								},
								{
									"name": "Price",
									"value": f"`₹ {self.prodPrice}`",
									"inline": True
								},
								{
									"name": "Checkout Time",
									"value": f"`{str(datetime.now() - startCheckoutTime)}`"
								},
								{
									"name": "Response",
									"value": f"```{_checkoutResp.text}```"
								},
								{
									"name": "Error Message",
									"value": f"`{errorCode}`"
								},
								{
									"name": "Phone number",
									"value": f"||{str(self.login_phone)}||"
								}
							],
							"footer": {
								"text": "Myntra Bot",
								"icon_url": "https://logos-world.net/wp-content/uploads/2021/02/New-Myntra-Logo.png"
							},
							"timestamp": datetime.utcnow().isoformat(),
							"thumbnail": {
								"url": self.prodImage
							}
						}
					],
					"username": "Myntra Bot",
					"avatar_url": "https://res.cloudinary.com/crunchbase-production/image/upload/c_lpad,f_auto,q_auto:eco,dpr_1/v1499793144/wq1zrsfvi5pep2zwyxyi.png",
					"attachments": []
				}
			)

	def clearCart(self):

		# Clear Cart
		while True:
			# self.consoleLog(f'{Fore.YELLOW}Clearing Cart')

			try:
				_crt_resp = self.myntraGetCart().text
				if DEBUG:
					logging.info(f'CART RESPONSE: {_crt_resp}')

				_json_cart = json.loads(_crt_resp)

				self.cartID = _json_cart['id']
				self.userID = _json_cart['createdBy']

				_items = []
				for item in _json_cart['products']:
					self.consoleLog(f'{Fore.YELLOW}Removing {item["name"]}')

					_items.append({
						'itemId': item["itemId"]
					})

				if len(_items) == 0:
					# self.consoleLog(f'{Fore.YELLOW}Cart is already empty!')
					return

				self.myntraClrCart(_items)
				return

			except (ValueError, Exception) as _e:
				self.consoleLog(
					f'{Fore.RED}Error clearing Cart -> Refreshing token | {str(_e)} | {traceback.format_exc()}')
				self.refreshAccessToken()

	def refreshAccessToken(self):

		while True:
			self.consoleLog(f'{Fore.GREEN}Refreshing access tokens')

			try:
				refresh_Headers = _at = self.myntraRefreshSession().headers

				_at = refresh_Headers['at']
				_rt = refresh_Headers['rt']

				self.myntraSession.headers["at"] = _at
				self.myntraSession.cookies["at"] = _at

				self.myntraSession.headers["rt"] = _rt
				self.myntraSession.cookies["rt"] = _rt

				self.captchaEngine.updateSession(self.myntraSession.cookies, self.myntraSession.headers)

				self.consoleLog(f'{Fore.GREEN}Refreshed access token')
				break

			except (ValueError, Exception) as _e:
				self.consoleLog(f'{Fore.GREEN}Error refreshing access tokens | {str(_e)}')

	def checkWishlist(self):

		# Clear Cart
		self.clearCart()

		try:
			_wishlist = self.myntraGetWishList().text
			if DEBUG:
				logging.info(f'WISHLIST RESPONSE: {_wishlist}')
			wishlist = json.loads(_wishlist)

		except (ValueError, Exception):
			return False

		try:

			oos_items = 0

			for style in wishlist["styles"]:

				# We need the ID to cart
				_styleID = style["id"]
				self.prodImage = style["searchImage"]
				self.prodName = style['name']

				instock_Items = list(filter(lambda v: v['available'], style["inventoryInfo"]))

				if len(instock_Items) == 0:
					# self.consoleLog(f"{Fore.YELLOW}[+] OOS: {style['name']}")
					oos_items += 1
					continue

				self.consoleLog(f"{Fore.YELLOW}[+] FOUND IN-STOCK ITEMS: {style['name']}")

				for _itemIndex in range(0, self.preferenceSizes):
					# We might get a value Error here so just in case
					try:
						_skuID = instock_Items[_itemIndex]["skuId"]
						_stockCount = instock_Items[_itemIndex]["sellersData"][0]["availableCount"]
						_sellerPartnerId = instock_Items[_itemIndex]["sellersData"][0]["sellerPartnerId"]

						self.prodPrice = instock_Items[_itemIndex]["sellersData"][0]["discountedPrice"]
						self.prodSize = instock_Items[_itemIndex]["label"]
						self.prodStock = _stockCount

						self.consoleLog(
							f"{Fore.GREEN}[+] ADDING TO CART: {style['name']} | {instock_Items[_itemIndex]['label']} (Stock: {_stockCount})")

						_atc_resp = self.myntraATC(_styleID, _sellerPartnerId, _skuID)
						if DEBUG:
							logging.info(f'ATC RESP: {_atc_resp.text}')

						self.cartID = json.loads(_atc_resp.text)['id']
						self.myntraPutAddress()

						# Start Checkout Flow
						self.copyCookies()
						self.checkoutFlow()

					except (Exception, ValueError) as _e:
						self.consoleLog(f'{Fore.RED}[Non-critical Error] Item out of bounds > {str(_e)}')

			self.consoleLog(f"{Fore.YELLOW}[+] OOS: {oos_items} Items")

		except (ValueError, Exception) as _e:
			self.consoleLog(f'{Fore.RED}Error checking Wishlist | {str(_e)}')

	def copyCookies(self):
		self.myntraSession.cookies['at'] = self.myntraSession.headers['at']
		self.myntraSession.cookies['rt'] = self.myntraSession.headers['rt']
		self.myntraSession.cookies['user_uuid'] = self.myntraSession.headers['user_uuid']

	def setSizePreference(self, _newSize):
		self.preferenceSizes = _newSize

	def run(self):

		while not self.running:
			time.sleep(1)

		# Get Access Token
		while True:
			self.consoleLog(f'{Fore.YELLOW}Getting access token')

			try:
				_at = self.myntraGetAtToken().headers['at']

				self.myntraSession.headers["at"] = _at
				self.consoleLog(f'{Fore.GREEN}Got access token')

				break
			except (ValueError, Exception) as _e:
				self.consoleLog(f'{Fore.RED}Error getting access token | {str(_e)}')

		# Login to Account
		while True:
			self.consoleLog(f'{Fore.YELLOW}Logging in')

			try:
				_login = self.myntraLogin()
				logging.info(f'LOGIN RESP | {_login.text}')

				if _login.status_code == 200 and _login.headers["rt"] and _login.headers["at"]:
					self.consoleLog(f'{Fore.GREEN}Logged in successfully')

					# Set refresh & access token
					self.myntraSession.headers["at"] = _login.headers["at"]
					self.myntraSession.headers["rt"] = _login.headers["rt"]
					self.uidx = json.loads(_login.text)["uidx"]

					# Set Session Cookies
					self.myntraSession.headers['user_uuid'] = self.uidx

					break

				if 'TOO_MANY_FAILED_PASSWORD_ATTEMPTS' in _login.text:
					self.consoleLog(f'{Fore.GREEN}Too many failed password attempts | Retrying in 300 seconds')
					time.sleep(300)

			except (ValueError, Exception) as _e:
				self.consoleLog(f'{Fore.GREEN}Error logging in | {str(_e)}')

		# Set Address Values
		while True:
			self.consoleLog(f'{Fore.YELLOW}Getting Account Information')

			try:
				_addresses = self.myntraGetAddress()

				_json_add = json.loads(_addresses.text)

				for address in _json_add['addresses']:
					if address['isDefault']:
						self.addressID = address['id']

				self.consoleLog(f'{Fore.GREEN}Got Account Information')

				break

			except (ValueError, Exception) as _e:
				self.consoleLog(f'{Fore.RED}Error Getting Account Information/Address {str(_e)}')

		# Start captchaBank
		self.captchaEngine = CaptchaEngine(self.myntraSession, self.preSolve_Amount)
		self.captchaEngine.start()

		# Set start time, so we can refresh access tokens every 15 minutes
		lastLoginUNIX_TS = datetime.now()

		# Check if any Item is in Stock
		while True:

			# If last refresh is past 45 minutes refresh access token
			if self.running:
				if (datetime.now() - lastLoginUNIX_TS) > timedelta(minutes=45):
					self.refreshAccessToken()
					lastLoginUNIX_TS = datetime.now()

				self.checkWishlist()

				# self.consoleLog(f'{Fore.YELLOW}Delaying for next Wishlist Check')
				time.sleep(self.delay)
			else:
				time.sleep(1)


# Read Tasks.csv File and create tasks
threads = []

with open('Tasks.csv', 'r') as _taskFile:
	csvreader = csv.reader(_taskFile)
	for _account in csvreader:
		# Headers row shall be skipped
		if 'RUN' in str(_account):
			continue
		threads.append(MyntraTask(_account[0], _account[1], int(_account[3]), int(_account[2])))

for task in threads:
	task.start()

while True:
	try:
		with open('Tasks.csv', 'r') as _taskFile:
			csvreader = csv.reader(_taskFile)
			for _account in csvreader:
				# Headers row shall be skipped
				if 'RUN' in str(_account):
					continue

				active = _account[2]
				new_size_preference = _account[3]

				for thread in threads:
					# Change if active
					if _account[0] == thread.login_phone:

						# Change active
						if int(thread.running) is not int(active):
							if not bool(int(active)):
								print(f'{Fore.RED}PAUSING THREAD: {thread.login_phone}')
							else:
								print(f'{Fore.GREEN}RESUMING THREAD: {thread.login_phone}')
							thread.running = int(active)

						# Change size preference
						if int(thread.preferenceSizes) != int(new_size_preference):
							print(
								f'{Fore.GREEN}UPDATED SIZE PREFERENCE: {thread.login_phone} [{thread.preferenceSizes} -> {new_size_preference}]')
							logging.info(
								f'UPDATED SIZE PREFERENCE: {thread.login_phone} [{thread.preferenceSizes} -> {new_size_preference}]')
							thread.setSizePreference(new_size_preference)

	except (PermissionError, Exception) as _e:
		print(str(_e))
		pass

	time.sleep(5)
