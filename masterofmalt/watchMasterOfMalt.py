import os
from threading import Thread
import requests
import time
import json
from configparser import ConfigParser

WATCHDOG_PATH = os.getcwd() + '/watchMOMDog.sh'
ITEMJSON_PATH = os.getcwd() + '/masterofmalt.json'
COOKIE_FILE_PATH = os.getcwd() + '/cookie'
HEADERS = {'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
    
BASE_URL = 'https://www.masterofmalt.com/api/data/productstracking/'

config = ConfigParser()
config.load('masterofmalt.ini')
SLACK_TOKEN = config['slack']['token']
SLACK_CHANNEL = config['slack']['channel']

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
        headers={"Authorization": "Bearer "+SLACK_TOKEN},
        data={"channel": SLACK_CHANNEL,"text": text})
        time.sleep(1)


def getStockInfoMOM(code):
    result = ""
    r = requests.get(BASE_URL + code, headers=HEADERS)
    
    try:
        ret = json.loads(r.content)
        result = ret['products'][0]['available']
    except:
        if '403' in str(r):
            sendMessage('API Blocked, Please update cookie',2)
        else:
            sendMessage('Unknown Error occurred!\n' + str(r),2)
    return str(result)


def getWatchList(jsonData):
    itemString = ''
    for it in jsonData['itemList']:
        itemString += it['name'] + '\n'
    return itemString


def chechItem(item,errorCount):
    result = getStockInfoMOM(item['code'])
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
            item['reTryCount'] = 50
            text = item['name'] + '\n' + item['link']
            sendMessage(text,16)
    elif item['reTryCount'] > 0: #case disavailable
        item['reTryCount'] = 0

        
if __name__ == "__main__":
    with open(COOKIE_FILE_PATH, 'r') as cookieFile:
        HEADERS["cookie"] = cookieFile.readline().strip('\n')
    print(HEADERS)
    with open(ITEMJSON_PATH, 'r') as jsonFile:
        itemData = json.load(jsonFile)
        startMsg = 'Start watching MasterOfMalt\n' + '============= itemList =============\n' + getWatchList(itemData) + '===================================='
        t = Thread(target=sendMessage, args=(startMsg,2,), daemon=True)
        t.start()
        t.join()
        errorCount = 0
        while True:
            for item in itemData['itemList']:
                chechItem(item,errorCount)
                print('check ' + item['name'])
                time.sleep(1)
            time.sleep(10)
