import os
from threading import Thread
import requests
import time
import json
from configparser import ConfigParser
import logging

config = ConfigParser()
config.read('masterOfMalts.ini')

logging.basicConfig(filename="masterOfMalts.log", level=logging.INFO)

ITEMJSON_PATH = os.getcwd() + '/nickollsandperks.json'

HEADERS = {'Content-Type': 'application/json'}
BASE_URL = 'https://www.nickollsandperks.co.uk/api/items?c=4430378&fieldset=details&url='

# ========================================================= #
#                    JSON Object struct                     #
# {                                                         #
#     "itemList" : [                                        #
#         {                                                 #
#             'name' : 'item's name',                       #
#             'link' : 'page Address to purchase,           #
#             'code' : "special key for distinguish item",  #
#             'reTryCount': 0                               #
#         },                                                #
#     ]                                                     #
# }                                                         #
# ========================================================= #

def sendMessage(text, sendCount):
    for i in range(1,sendCount):
        requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+ config['slack']['token']},
        data={"channel":  '#' + config['slack']['channel'],"text": text})
        time.sleep(1)


def getStockInfoNAP(code):
    result = ""
    try:
        r = requests.get(BASE_URL + code, headers=HEADERS)
        ret = json.loads(r.content)
        result = ret['items'][0]['isinstock']
    except:
        result = 'error'
    return str(result)


def getWatchList(jsonData):
    itemString = ''
    for it in jsonData['itemList']:
        itemString += it['name'] + '\n'
    return itemString


def chechItem(item, errorCount):
    result = getStockInfoNAP(item['code'])
    if result == 'error':
        errorCount += 1
        if (errorCount > 50):
            text = 'watch dog is dead!!!!!\n During Request'
            sendMessage(text,2)
        return
    
    if errorCount != 0:
        errorCount = 0
    
    if result == 'True':
        if item['reTryCount'] > 0:
            item['reTryCount'] -= 1
        else:
            item['reTryCount'] = 500
            text = item['name'] + '\n' + item['link']
            sendMessage(text,16)
    elif item['reTryCount'] > 0: #case disavailable
        item['reTryCount'] = 0


if __name__ == "__main__":
    with open(ITEMJSON_PATH, 'r') as jsonFile:
        itemData = json.load(jsonFile)
        startMsg = 'Start watching NickollsAndPerks\n' + '============= itemList =============\n' + getWatchList(itemData) + '===================================='
        t = Thread(target=sendMessage, args=(startMsg,2,), daemon=True)
        t.start()
        t.join()
        errorCount = 0
        while True:
            for item in itemData['itemList']:
                t = Thread(target=chechItem, args=(item,errorCount,), daemon=True)
                t.start()
            time.sleep(10)
