import random
import ast
import os
import requests
import time
import json
import schedule
import logging
import platform
from threading import Thread
from configparser import ConfigParser
from selenium import webdriver
from dataclasses import dataclass 
from datetime import date
from datetime import datetime
from flask import Flask, request, jsonify

HEADERS = {'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
NEW_ARRIVAL_ADDRESS = "https://www.masterofmalt.com/new-arrivals/whisky-new-arrivals/"
TRACKING_ADDRESS = "https://www.masterofmalt.com/api/data/productstracking/"
CHECKOUT_ADDRESS = "https://www.masterofmalt.com/checkout/address/"

config = ConfigParser()
config.read('masterOfMalts.ini')

apiApp = Flask(__name__)

logging.basicConfig(filename="masterOfMalts.log", level=logging.INFO)

m_lastNewProductIDs = ""
m_lastNewProductInfos = []
m_sentList = []
bootEvent = True

# ------ Error Code ------- #
INVALID_WATCH_TARGET = -100
INVALID_USER_INFO = -200


# ------ Data Structure ------ # 
@dataclass 
class userInfo: 
    id: str
    passwd: float
    lastCheckoutTime: date = datetime.now()
    checkoutAvailable: bool = True


@dataclass 
class watchItem:
    prodName: str 
    prodId: str
    autoCheckOut: bool


@dataclass
class productInfo:
    prodId: int
    prodName: str
    prodPrice : int

# ----- Web Obect Control ----- #
def createWebObj():
    global m_driver
    chrome_options = webdriver.ChromeOptions()
    
    if platform.system() != 'Windows':
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--disable-dev-shm-usage')
    
    m_driver = webdriver.Chrome(config['chrome']['enginePath'], chrome_options=chrome_options)
    time.sleep(1)
    

def webObjInit():
    createWebObj()
    login()
    m_driver.get(NEW_ARRIVAL_ADDRESS)
    

def reCreateWebObj():
    m_driver.close()
    sendMessage('### Sleep 10 Min to reopen webPage ###', 2, "Notice")
    time.sleep(600)
    webObjInit()
    sendMessage('### reopen webPage ###', 2, "Notice")
    bootEvent = True
    

def login():
    m_driver.get("https://www.masterofmalt.com")
    time.sleep(10)
    for i in range(0,10) :
        onetrustBtn = m_driver.execute_script('btn = document.getElementById(\'onetrust-accept-btn-handler\'); return btn;')
        if onetrustBtn is not None :
            m_driver.execute_script('document.getElementById(\'onetrust-accept-btn-handler\').click();')
            logging.info("click onetrust-accept-button")
            break
        time.sleep(1)

    for i in range (0,10) :
        popupBtn = m_driver.execute_script('btn = document.getElementById(\'InternationalPopupConfirmation\'); return btn;')
        if popupBtn is not None :
            m_driver.execute_script('document.getElementById(\'InternationalPopupConfirmation\').click();')
            logging.info("click InternationalPopupConfirmation-button")
            break
        time.sleep(1)

    time.sleep(5)
    m_driver.get("https://www.masterofmalt.com/#context-login")
    time.sleep(5)
    m_driver.execute_script('txtLoginEmail.value=\"' + m_userInfoes[0].id + '\";txtLoginPassword.value=\"' + m_userInfoes[0].passwd + '\";document.getElementById(\'MOMBuyButton\').click();')
    time.sleep(5)


# ----- New Arrive Products Manage ----- #
def refreshAndGetNewProductIds():    
    logging.info("Refresh page\n")
    m_driver.refresh()
    m_driver.implicitly_wait(15)
    idString = ""
    prodinfo = []
    dataLayer = m_driver.execute_script('var iDs = window.dataLayer; return iDs')
    for data in dataLayer:
        if ("productIDs" in data):
            prodIds = data['productIDs']
            prodNames = data['productNames']
            prodPrices = data['productPrices']
            idString = ','.join(map(str, prodIds))
            for i in range(0, len(prodIds)):
                prodinfo.append(productInfo(prodIds[i], prodNames[i], prodPrices[i]))
            break
    logging.info("refreshed idString : " + idString)    
    return idString, prodinfo


def getProductInfoes(idString):
    r = requests.get(TRACKING_ADDRESS + idString, headers=HEADERS)
    try:
        ret = json.loads(r.content)
    except:
        if '403' in str(r):
            sendMessage('API Blocked', 2, "Notice")
        elif '520' in str(r):
            sendMessage('520 Error, skip this try\n' + str(r), 2, "Error")
            return ""
        else:
            sendMessage('Unknown Error occurred!\n' + str(r), 2, "Error")
        return
    retString = str(r.content)
    retString = retString.replace("\\","")
    retString = retString.replace("'","")
    retString = retString[1:]
    logging.info("proDuct info : " + retString)
    return retString


# ----- Data Parsing ----- #
def parseNewProductKeys():
    global m_newItmeKeys 
    m_newItmeKeys = str(config['newProducts']['names']).split('&')
    logging.info("watching New Product List : " + str(m_newItmeKeys))


def parseUserAuthData():
    global m_userInfoes
    m_userInfoes = []

    userIDs = ast.literal_eval(config.get("user", "ID"))
    userPWs = ast.literal_eval(config.get("user", "passwd"))
    if len(userIDs) != len(userPWs) :
        return False

    for i in range(len(userIDs)):
        userInfo(id="",passwd="",)
        m_userInfoes.append(userInfo(id=userIDs[i],passwd=userPWs[i]))
    logging.info(m_userInfoes)
    return True


def parseWachingListProducts():
    global m_watchList
    global m_watchItems
    m_watchList = ""
    m_watchItems = []

    with open(os.getcwd() + '/masterOfMalts.json', 'r', encoding='UTF8') as jsonFile:
        itemData = json.load(jsonFile)
        for item in itemData['itemList']:
            m_watchList = m_watchList + item['code'] + ','
            m_watchItems.append(watchItem(item['name'],item['code'],item['autoCheckOut']))
        m_watchList = m_watchList[:-1]
    logging.info("m_watchList : " + m_watchList)
    print(m_watchItems)


def checkNewProductInfoes(newProdInfos : productInfo):
    for prod in newProdInfos:        
        if prod.prodId not in m_sentList:
            if str(prod.prodId) in m_lastNewProductIDs:
                for key in m_newItmeKeys :
                    if (key in prod.prodName):
                        sendStockAlarm(False, prod.prodName, prod.prodId)


def checkWatchingProductInfoes(jsonString : str):
    jsonData = json.loads(jsonString)
    products = jsonData['products']
    for item in products:
        prodId = int(item['productID'])
        prodName = item['name'].lower()
        avab =  item['available']     
        
        if avab == True and prodId not in m_sentList:
            if isSwitchOn(prodId) :
                checkOutTheItem(prodId)
            sendStockAlarm(True, prodName, prodId)


# ----- Utills  ----- #
def sendMessage(text, sendCount, channelType):
    if channelType == "Notice":
        channel = config['slack']['channel']
    elif channelType == "Personal":
        channel = config['slack']['personalChannel']
    elif channelType == "Error":
        channel = config['slack']['ErrorChannel']
    
    try:
        slackHeaders = {"Authorization": "Bearer "+ config['slack']['token']}
        slackDatas = {"channel": '#' + channel,"text": text}
        for i in range(1,sendCount):
            requests.post("https://slack.com/api/chat.postMessage",
            headers=slackHeaders,
            data=slackDatas)
            time.sleep(0.5)
    except:
        logging.error("### error occur during sendMessage. msg : " + text)


def sendNewProductInfos(newProdInfos):
    newProductListMsg = "### New Item Arrived, Check New List ###"
    for newInfo in newProdInfos:
        isNew = True
        for info in m_lastNewProductInfos:
            if (info.prodId == newInfo.prodId):
                isNew = False
                break
        if (isNew):
            newProductListMsg += "\n- name: " + newInfo.prodName + ", price : " + str(newInfo.prodPrice) + "(InclTax)"

    sendMessage(newProductListMsg, 2, "Notice")
            


def sendStockAlarm(reStock : bool, name : str, prodId : int):
    logging.info("checkOutTheItem item : " + str(prodId))
    if reStock:
        text = "###### Re-Stock ######\n"
    else:
        text = "###### NEW STOCK ######\n"
    text = text + name + " Arrived !!\n"
    text = text + "https://www.masterofmalt.com/s/?q=" + name + "&size=n_25_n"
    sendMessage(text, 5, "Notice")
    logging.info(text)
    m_sentList.append(prodId)


def resetDatas():
    m_sentList.clear()
    for info in m_userInfoes:
        info.checkoutAvailable = True
    sendMessage("### Reset Datas ###", 2, "Notice")    


def isSwitchOn(targetId) :
    for item in m_watchItems:
        if item.prodId == str(targetId) :
            return item.autoCheckOut
    return False


def checkOutTheItem(prodId : int) :
    totalCount = m_driver.execute_script('var total = getBasketQuantityTotal(); return total')
    logging.info('check out , totalCount : ' + str(totalCount))
    if totalCount == 0 and m_userInfoes[0].checkoutAvailable :
        logging.info("checkOutTheItem item : " + str(prodId))
        m_driver.execute_script('AddToBasket(' + str(prodId) + ')') 
        logging.info("Add itme, item : " + str(prodId))
        time.sleep(1)
        m_driver.get(CHECKOUT_ADDRESS)
        time.sleep(3)
        
        while True:
            try :
                m_driver.execute_script('document.getElementsByName(\'disclaimer-checkbox\')[1].click()')
                break
            except:
                time.sleep(0.5)
        while True:
            try :
                m_driver.execute_script('document.body.getElementsByClassName(\'mom-btn mom-btn-large mom-btn-green-alt mom-btn-full-width\')[0].click();')
                break
            except:
                time.sleep(0.5)

        sendMessage("##### checkout tried ##### ", 5, "Personal")
        m_userInfoes[0].checkoutAvailable = False
        logging.info("Successfully auto-checkout item, code : " + str(prodId))
    else :
        text = "###### watch List re-stock, but just add to basket ######\n"
        text = text + ""
        sendMessage(text, 5, "Personal")
    

# ----- API  ----- #
@apiApp.route('/add/watchItem', methods=['POST'])
def addWatchItem():
    params = request.get_json()
    logging.info('ADD watch List Item API called, params : ' + str(params))

    m_watchList += (',' + str(params['prodId']))
    m_watchItems.append(watchItem(params['name'],params['prodId'],params['autoCheckout']))
    
    response = {
        "result": "ok",
        "m_watchList": str(m_watchList),
        "m_watchItems": str(m_watchItems)
    }
    
    sendMessage("ADD watch List Item by API, item : " + params['name'])
    return jsonify(response)


def runApiServer():
    apiApp.run(host='0.0.0.0', port=8080)


if __name__ == "__main__":

    parseNewProductKeys()
    parseWachingListProducts()
    if len(m_watchList) == 0 and len(m_newItmeKeys) == 0 :
        print("ERROR: Threr is no item to watch!")
        exit(INVALID_WATCH_TARGET)
    
    parseUserAuthData()
    print(m_userInfoes)
    if len(m_userInfoes) == 0 :
        print("ERROR: There is no user info to use")
        exit(INVALID_USER_INFO)
    
    webObjInit()

    watchingSpan = int(config['etc']['watchingSpan'])
    watchCount = 0
    
    schedule.every().day.at(config['etc']['resetTime']).do(resetDatas)
    schedule.run_pending()
    
    apiThread = Thread(target=runApiServer)
    apiThread.start()

    while True:
        watchCount = watchCount + 1    
        if watchCount % watchingSpan == 0:
            sendMessage("### still watching ###", 2, "Notice")
            watchCount = 0

        try:
            idString, newProdInfos = refreshAndGetNewProductIds()
            if (m_lastNewProductIDs != idString) :
                if not bootEvent:
                    sendNewProductInfos(newProdInfos)
                else:
                    bootEvent = False
                m_lastNewProductIDs = idString
                m_lastNewProductInfos = newProdInfos
                logging.info('New Product IDs : ' + idString + '\n')
                checkNewProductInfoes(newProdInfos)            
        except Exception as e:
                sendMessage("### Error occur during get New Products info", 2, "Error")
                sendMessage("Error info \n" + str(e), 2, "Error")
                reCreateWebObj()

        try:
            jsonString = getProductInfoes(m_watchList)
            if len(jsonString) == 0 :
                    continue
            checkWatchingProductInfoes(jsonString)
        except Exception as e:
            sendMessage("### Error occur during get watching products info", 2, "Error")
            sendMessage("Error info \n" + str(e), 2, "Error")
            reCreateWebObj()

        time.sleep(random.randrange(30,60))