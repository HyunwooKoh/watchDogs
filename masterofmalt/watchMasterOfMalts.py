import random
import os
import requests
import time
import json
from selenium import webdriver
import logging
from configparser import ConfigParser

HEADERS = {'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
NEW_ARRIVAL_ADDRESS = "https://www.masterofmalt.com/new-arrivals/whisky-new-arrivals/"
TRACKING_ADDRESS = "https://www.masterofmalt.com/api/data/productstracking/"

config = ConfigParser()
config.read('masterOfMalts.ini')

logging.basicConfig(filename="masterOfMalts.log", level=logging.INFO)

m_lastNewProductIDs = ""
m_sentList = []

# ----- Web Obect Control ----- #
def createWebObj():
    global m_driver
    m_driver = webdriver.Chrome(config['chrome']['enginePath'])


def webObjInit():
    createWebObj()
    login()
    m_driver.get(NEW_ARRIVAL_ADDRESS)
    

def reCreateWebObj():
    m_driver.close()
    sendMessage('### Sleep 10 Min to reopen webPage ###',2)
    time.sleep(600)
    webObjInit()
    sendMessage('### reopen webPage ###',2)
    

def login():
    m_driver.get("https://www.masterofmalt.com")
    time.sleep(10)
    m_driver.execute_script('document.getElementById(\'onetrust-accept-btn-handler\').click();')
    m_driver.execute_script('document.getElementById(\'InternationalPopupConfirmation\').click();')
    time.sleep(5)
    m_driver.get("https://www.masterofmalt.com/#context-login")
    time.sleep(5)
    m_driver.execute_script('txtLoginEmail.value=\"' + config['user']['ID'] + '\";txtLoginPassword.value=\"' + config['user']['passwd'] + '\";document.getElementById(\'MOMBuyButton\').click();')
    time.sleep(5)


# ----- New Arrive Products Manage ----- #
def refreshAndGetNewProductIds():    
    logging.info("Refresh page\n")
    m_driver.refresh()
    m_driver.implicitly_wait(2)
    idString = ""
    dataLayer = m_driver.execute_script('var iDs = window.dataLayer; return iDs')
    for data in dataLayer:
        if ("productIDs" in data):
            result = data['productIDs']
            idString = ','.join(map(str, result))
    return idString


def getProductInfoes(idString):
    r = requests.get(TRACKING_ADDRESS + idString, headers=HEADERS)
    try:
        ret = json.loads(r.content)
    except:
        if '403' in str(r):
            sendMessage('API Blocked', 2)
        else:
            sendMessage('Unknown Error occurred!\n' + str(r),2)
        return
    retString = str(r.content)
    retString = retString.replace("\\","")
    retString = retString.replace("'","")
    retString = retString[1:]
    return retString


# ----- Data Parsing ----- #
def parseNewProductKeys():
    global m_keys 
    m_keys = config['newProducts']['names'].split('&')
    logging.info("watching New Product List : " + str(m_keys))


def parseWachingListProducts():
    global m_watchList
    m_watchList = ""
    
    with open(os.getcwd() + '/masterOfMalts.json', 'r', encoding='UTF8') as jsonFile:
        itemData = json.load(jsonFile)
        for item in itemData['itemList']:
            m_watchList = m_watchList + item['code'] + ','
        m_watchList = m_watchList[:-1]
    print(m_watchList + "\n")
    logging.info("m_watchList : " + m_watchList)


def checkProductInfoes(jsonString):
    jsonData = json.loads(jsonString)
    products = jsonData['products']
    for item in products:
        prodId = item['productID']
        prodName = item['name'].lower()
        avab =  item['available']     
        
        if avab == True and prodId not in m_sentList:
            if str(prodId) in m_lastNewProductIDs:
                for key in m_keys :
                    if (key in prodName):
                        sendStockAlarm(False, prodName, prodId)
            else:
                sendStockAlarm(True, prodName, prodId)


# ----- Utills  ----- #
def sendMessage(text, sendCount):
    try:
        for i in range(1,sendCount):
            requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer "+ config['slack']['token']},
            data={"channel": '#' + config['slack']['channel'],"text": text})
            time.sleep(1)
    except:
        logging.error("### error occur during sendMessage. msg : " + text)


def sendStockAlarm(reStock, name, prodId):
    if reStock:
        text = "###### Re-Stock ######\n"
    else:
        text = "###### NEW STOCK ######\n"
    text = text + name + " Arrived !!\n"
    text = text + "https://www.masterofmalt.com/s/?q=" + name + "&size=n_25_n"
    print("send target item incomed message")
    sendMessage(text,5)
    m_driver.execute_script('AddToBasket(' + str(prodId) + ')')
    m_sentList.append(prodId)


# TODO
# def resetSentList() : reset m_sentList in evry 24 hours.
# def purchaseItemInBuske() : check out the users busket


if __name__ == "__main__":
    parseNewProductKeys()
    parseWachingListProducts()
    webObjInit()
    watchingSpan = int(config['etc']['watchingSpan'])
    watchCount = 0
    while True:
        watchCount = watchCount + 1    
        if watchCount % watchingSpan == 0:
            sendMessage("### still watching ###", 2)
            watchCount = 0

        try:
            idString = refreshAndGetNewProductIds()
            if (m_lastNewProductIDs != idString) :
                sendMessage("### New Item Arrived, Check New List ###", 2)
                m_lastNewProductIDs = idString
                jsonString = getProductInfoes(idString)
                logging.info('New Product IDs : ' + idString + '\n')
                checkProductInfoes(jsonString)                
        except:
                sendMessage("### Error occur during get New Products info", 2)
                reCreateWebObj()

        try:
            jsonString = getProductInfoes(m_watchList)
            checkProductInfoes(jsonString)
        except:
            sendMessage("### Error occur during get watching products info", 2)
            reCreateWebObj()

        time.sleep(random.randrange(30,60))