# ====================== - ======================== #
#                   Class: Webhook                  #
#        Usage: Simplify Discord Webhook sending    #
# ======================= - ======================= #
import requests


def send_webhook(_webhookURL: str, _webhookContent):
	requests.post(
		url=_webhookURL,
		json=_webhookContent
	)




def mossad():
	return True
